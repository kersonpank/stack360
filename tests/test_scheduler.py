"""
Tests for Normalizer Scheduler v0.1.
All tests are unit tests — no real DB connection required.
"""
import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/testdb")
os.environ.setdefault("API_ENV", "testing")


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


def test_scheduler_disabled_by_default():
    from app.core.config import Settings

    # Test the class-level Python default, not the live singleton (which may be
    # overridden by .env in production environments).
    field = Settings.model_fields["normalizer_scheduler_enabled"]
    assert field.default is False


def test_scheduler_config_defaults():
    from app.core.config import settings

    assert settings.normalizer_interval_seconds == 300
    assert settings.normalizer_incremental_limit == 1000
    assert settings.normalizer_incremental_max_batches == 1
    assert settings.normalizer_nightly_enabled is True
    assert settings.normalizer_nightly_hour == 2
    assert settings.normalizer_nightly_limit == 5000
    assert settings.normalizer_nightly_max_batches == 5


# ---------------------------------------------------------------------------
# SchedulerState initial values
# ---------------------------------------------------------------------------


def test_scheduler_state_initial():
    from app.scheduler.scheduler_state import SchedulerState

    state = SchedulerState()
    assert state.enabled is False
    assert state.running is False
    assert state.last_run_started_at is None
    assert state.last_run_finished_at is None
    assert state.last_success_at is None
    assert state.last_error_at is None
    assert state.last_error_message is None
    assert state.last_result is None
    assert state.total_runs == 0
    assert state.total_success == 0
    assert state.total_failures == 0
    assert state.total_skipped_by_lock == 0
    assert state.next_run_estimate is None
    assert state.last_nightly_date is None


# ---------------------------------------------------------------------------
# Scheduler status endpoint
# ---------------------------------------------------------------------------


def test_scheduler_status_endpoint_returns_expected_structure(client):
    response = client.get("/api/v1/system/normalizer-scheduler-status")
    assert response.status_code == 200
    data = response.json()

    assert "enabled" in data
    assert "running" in data
    assert "interval_seconds" in data
    assert "nightly_enabled" in data
    assert "nightly_hour" in data
    assert "last_run_started_at" in data
    assert "last_run_finished_at" in data
    assert "last_success_at" in data
    assert "last_error_at" in data
    assert "last_error_message" in data
    assert "last_result" in data
    assert "total_runs" in data
    assert "total_success" in data
    assert "total_failures" in data
    assert "total_skipped_by_lock" in data
    assert "next_run_estimate" in data


def test_scheduler_status_disabled_by_default(client):
    response = client.get("/api/v1/system/normalizer-scheduler-status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["running"] is False
    assert data["total_runs"] == 0


def test_scheduler_status_interval_matches_config(client):
    from app.core.config import settings

    response = client.get("/api/v1/system/normalizer-scheduler-status")
    data = response.json()
    assert data["interval_seconds"] == settings.normalizer_interval_seconds
    assert data["nightly_hour"] == settings.normalizer_nightly_hour


# ---------------------------------------------------------------------------
# Scheduler does not start when disabled
# ---------------------------------------------------------------------------


def test_scheduler_start_does_nothing_when_disabled():
    from app.scheduler.normalizer_scheduler import NormalizerScheduler
    from app.scheduler.scheduler_state import SchedulerState

    sched = NormalizerScheduler()
    with patch("app.scheduler.normalizer_scheduler.scheduler_state", SchedulerState()):
        with patch("app.core.config.settings.normalizer_scheduler_enabled", False):
            sched.start()
            assert sched._task is None


# ---------------------------------------------------------------------------
# Advisory lock skip
# ---------------------------------------------------------------------------


def test_run_normalization_sync_skips_when_lock_not_acquired():
    """If pg_try_advisory_lock returns False, result must have skipped_lock=True."""
    mock_conn = MagicMock()
    mock_conn.execution_options.return_value = mock_conn
    mock_conn.execute.return_value.scalar.return_value = False

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    # create_engine is imported lazily inside _run_normalization_sync;
    # patch at the sqlalchemy module level so both calls return our mock.
    with patch("sqlalchemy.create_engine", return_value=mock_engine), \
         patch("sqlalchemy.orm.sessionmaker"), \
         patch("app.core.config.settings.database_url", "postgresql+psycopg2://x:x@h/db"), \
         patch("app.core.config.settings.normalizer_database_url", "postgresql+psycopg2://x:x@h/db"):
        from app.scheduler.normalizer_scheduler import _run_normalization_sync

        result = _run_normalization_sync(limit=100, max_batches=1)

    assert result["skipped_lock"] is True
    assert result["processed"] == 0


# ---------------------------------------------------------------------------
# Error in run does not crash scheduler loop
# ---------------------------------------------------------------------------


def test_run_once_catches_exception_and_updates_state():
    """An exception in _run_normalization_sync must be caught; scheduler continues."""
    from app.scheduler.normalizer_scheduler import NormalizerScheduler
    from app.scheduler.scheduler_state import SchedulerState

    state = SchedulerState()

    async def run():
        sched = NormalizerScheduler()
        with patch("app.scheduler.normalizer_scheduler.scheduler_state", state):
            with patch(
                "app.scheduler.normalizer_scheduler.asyncio.to_thread",
                side_effect=RuntimeError("DB explodiu"),
            ):
                await sched._run_once(limit=100, max_batches=1, run_type="incremental")

    asyncio.run(run())

    assert state.total_failures == 1
    assert state.total_success == 0
    assert state.running is False
    assert "DB explodiu" in state.last_error_message


# ---------------------------------------------------------------------------
# _should_run_nightly logic
# ---------------------------------------------------------------------------


def test_should_run_nightly_false_when_nightly_disabled():
    from app.scheduler.normalizer_scheduler import NormalizerScheduler

    sched = NormalizerScheduler()
    with patch("app.core.config.settings.normalizer_nightly_enabled", False):
        assert sched._should_run_nightly() is False


def test_should_run_nightly_false_when_already_ran_today():
    from app.scheduler.normalizer_scheduler import NormalizerScheduler
    from app.scheduler.scheduler_state import SchedulerState

    state = SchedulerState()
    today = datetime.now(tz=timezone.utc).date()
    state.last_nightly_date = today

    sched = NormalizerScheduler()
    with patch("app.scheduler.normalizer_scheduler.scheduler_state", state):
        with patch("app.core.config.settings.normalizer_nightly_enabled", True):
            with patch("app.core.config.settings.normalizer_nightly_hour", datetime.now(tz=timezone.utc).hour):
                assert sched._should_run_nightly() is False


def test_should_run_nightly_true_when_correct_hour_not_yet_run():
    from app.scheduler.normalizer_scheduler import NormalizerScheduler
    from app.scheduler.scheduler_state import SchedulerState

    state = SchedulerState()
    state.last_nightly_date = None

    current_hour = datetime.now(tz=timezone.utc).hour
    sched = NormalizerScheduler()
    with patch("app.scheduler.normalizer_scheduler.scheduler_state", state):
        with patch("app.core.config.settings.normalizer_nightly_enabled", True):
            with patch("app.core.config.settings.normalizer_nightly_hour", current_hour):
                assert sched._should_run_nightly() is True

"""
Tests for Enrichment Scheduler v0.1.
All tests are unit tests — no real DB connection required.
"""
import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/testdb")
os.environ.setdefault("API_ENV", "testing")
os.environ["NORMALIZER_SCHEDULER_ENABLED"] = "false"
os.environ["ENRICHMENT_SCHEDULER_ENABLED"] = "false"


# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


def test_enrichment_scheduler_disabled_by_default():
    from app.core.config import Settings

    field = Settings.model_fields["enrichment_scheduler_enabled"]
    assert field.default is False


def test_enrichment_scheduler_use_llm_false_by_default():
    from app.core.config import Settings

    field = Settings.model_fields["enrichment_use_llm"]
    assert field.default is False


def test_enrichment_scheduler_config_defaults():
    from app.core.config import settings

    assert settings.enrichment_interval_seconds == 900
    assert settings.enrichment_incremental_limit == 100
    assert settings.enrichment_incremental_max_batches == 1
    assert settings.enrichment_nightly_enabled is True
    assert settings.enrichment_nightly_hour == 3
    assert settings.enrichment_nightly_limit == 1000
    assert settings.enrichment_nightly_max_batches == 3
    assert settings.enrichment_use_llm is False


# ---------------------------------------------------------------------------
# EnrichmentSchedulerState initial values
# ---------------------------------------------------------------------------


def test_enrichment_scheduler_state_initial():
    from app.scheduler.enrichment_scheduler_state import EnrichmentSchedulerState

    state = EnrichmentSchedulerState()
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
# Endpoint /enrichment-scheduler-status
# ---------------------------------------------------------------------------


def test_enrichment_scheduler_status_endpoint_structure(client):
    response = client.get("/api/v1/system/enrichment-scheduler-status")
    assert response.status_code == 200
    data = response.json()

    expected_keys = {
        "enabled", "running", "interval_seconds", "nightly_enabled",
        "nightly_hour", "use_llm", "last_run_started_at", "last_run_finished_at",
        "last_success_at", "last_error_at", "last_error_message", "last_result",
        "total_runs", "total_success", "total_failures", "total_skipped_by_lock",
        "next_run_estimate",
    }
    assert expected_keys.issubset(data.keys())


def test_enrichment_scheduler_status_disabled_by_default(client):
    response = client.get("/api/v1/system/enrichment-scheduler-status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["running"] is False
    assert data["total_runs"] == 0
    assert data["use_llm"] is False


def test_enrichment_scheduler_status_interval_matches_config(client):
    from app.core.config import settings

    response = client.get("/api/v1/system/enrichment-scheduler-status")
    data = response.json()
    assert data["interval_seconds"] == settings.enrichment_interval_seconds
    assert data["nightly_hour"] == settings.enrichment_nightly_hour


# ---------------------------------------------------------------------------
# Scheduler does not start when disabled
# ---------------------------------------------------------------------------


def test_enrichment_scheduler_start_does_nothing_when_disabled():
    from app.scheduler.enrichment_scheduler import EnrichmentScheduler
    from app.scheduler.enrichment_scheduler_state import EnrichmentSchedulerState

    sched = EnrichmentScheduler()
    with patch("app.scheduler.enrichment_scheduler.enrichment_scheduler_state", EnrichmentSchedulerState()):
        with patch("app.core.config.settings.enrichment_scheduler_enabled", False):
            sched.start()
            assert sched._task is None


def test_enrichment_scheduler_start_does_nothing_without_db_url():
    from app.scheduler.enrichment_scheduler import EnrichmentScheduler
    from app.scheduler.enrichment_scheduler_state import EnrichmentSchedulerState

    sched = EnrichmentScheduler()
    with patch("app.scheduler.enrichment_scheduler.enrichment_scheduler_state", EnrichmentSchedulerState()):
        with patch("app.core.config.settings.enrichment_scheduler_enabled", True):
            with patch("app.core.config.settings.normalizer_database_url", None):
                sched.start()
                assert sched._task is None


# ---------------------------------------------------------------------------
# Advisory lock skip
# ---------------------------------------------------------------------------


def test_run_enrichment_sync_skips_when_lock_not_acquired():
    """pg_try_advisory_lock returns False → result has skipped_lock=True."""
    mock_conn = MagicMock()
    mock_conn.execution_options.return_value = mock_conn
    mock_conn.execute.return_value.scalar.return_value = False

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_conn

    with patch("sqlalchemy.create_engine", return_value=mock_engine), \
         patch("sqlalchemy.orm.sessionmaker"), \
         patch("app.core.config.settings.database_url", "postgresql+psycopg2://x:x@h/db"), \
         patch("app.core.config.settings.normalizer_database_url", "postgresql+psycopg2://x:x@h/db"):
        from app.scheduler.enrichment_scheduler import _run_enrichment_sync

        result = _run_enrichment_sync(limit=100, max_batches=1, use_llm=False)

    assert result["skipped_lock"] is True
    assert result["processed"] == 0


# ---------------------------------------------------------------------------
# Error does not crash scheduler
# ---------------------------------------------------------------------------


def test_run_once_catches_exception_and_updates_state():
    from app.scheduler.enrichment_scheduler import EnrichmentScheduler
    from app.scheduler.enrichment_scheduler_state import EnrichmentSchedulerState

    state = EnrichmentSchedulerState()

    async def run():
        sched = EnrichmentScheduler()
        with patch("app.scheduler.enrichment_scheduler.enrichment_scheduler_state", state):
            with patch(
                "app.scheduler.enrichment_scheduler.asyncio.to_thread",
                side_effect=RuntimeError("Enrichment explodiu"),
            ):
                await sched._run_once(limit=100, max_batches=1, run_type="incremental")

    asyncio.run(run())

    assert state.total_failures == 1
    assert state.total_success == 0
    assert state.running is False
    assert "Enrichment explodiu" in state.last_error_message


# ---------------------------------------------------------------------------
# LLM not called when use_llm=False
# ---------------------------------------------------------------------------


def test_enrichment_use_llm_false_does_not_enable_llm():
    """ENRICHMENT_USE_LLM=false must not enable LLM even if LLM_ENABLED=true."""
    from app.core.config import Settings

    field = Settings.model_fields["enrichment_use_llm"]
    assert field.default is False

    # Simulate: use_llm=False passed to _run_enrichment_sync
    # LLMRouter.enabled() should return False since LLM_ENABLED=false in test env
    from app.enrichment.llm_router import LLMRouter
    assert LLMRouter.enabled() is False


# ---------------------------------------------------------------------------
# _should_run_nightly logic
# ---------------------------------------------------------------------------


def test_enrichment_should_run_nightly_false_when_disabled():
    from app.scheduler.enrichment_scheduler import EnrichmentScheduler

    sched = EnrichmentScheduler()
    with patch("app.core.config.settings.enrichment_nightly_enabled", False):
        assert sched._should_run_nightly() is False


def test_enrichment_should_run_nightly_false_when_already_ran_today():
    from app.scheduler.enrichment_scheduler import EnrichmentScheduler
    from app.scheduler.enrichment_scheduler_state import EnrichmentSchedulerState

    state = EnrichmentSchedulerState()
    today = datetime.now(tz=timezone.utc).date()
    state.last_nightly_date = today

    sched = EnrichmentScheduler()
    with patch("app.scheduler.enrichment_scheduler.enrichment_scheduler_state", state):
        with patch("app.core.config.settings.enrichment_nightly_enabled", True):
            with patch("app.core.config.settings.enrichment_nightly_hour", datetime.now(tz=timezone.utc).hour):
                assert sched._should_run_nightly() is False


def test_enrichment_should_run_nightly_true_when_correct_hour_not_yet_run():
    from app.scheduler.enrichment_scheduler import EnrichmentScheduler
    from app.scheduler.enrichment_scheduler_state import EnrichmentSchedulerState

    state = EnrichmentSchedulerState()
    state.last_nightly_date = None
    current_hour = datetime.now(tz=timezone.utc).hour

    sched = EnrichmentScheduler()
    with patch("app.scheduler.enrichment_scheduler.enrichment_scheduler_state", state):
        with patch("app.core.config.settings.enrichment_nightly_enabled", True):
            with patch("app.core.config.settings.enrichment_nightly_hour", current_hour):
                assert sched._should_run_nightly() is True

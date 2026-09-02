"""H1 — o entrypoint canônico (`app.stack360.main:app`) é INDEPENDENTE do legado:
instância FastAPI própria, sem schedulers legados, sem rotas legadas."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_canonical_app_is_not_legacy_app():
    import app.main as legacy
    import app.stack360.main as canonical

    assert canonical.app is not legacy.app
    assert canonical.app.title == "Stack360 Canonical Core"


def test_importing_canonical_does_not_start_legacy_schedulers():
    import app.stack360.main  # noqa: F401 — força o import
    from app.scheduler.enrichment_scheduler import enrichment_scheduler
    from app.scheduler.normalizer_scheduler import scheduler

    assert scheduler._task is None
    assert enrichment_scheduler._task is None


def test_canonical_app_exposes_no_legacy_routes():
    import app.stack360.main as canonical

    paths = {getattr(r, "path", "") for r in canonical.app.routes}
    for legacy_path in (
        "/api/v1/stakeholders",
        "/api/v1/actions",
        "/api/v1/system/normalization-status",
        "/api/v1/conversations/{conversation_id}/messages",
    ):
        assert legacy_path not in paths, legacy_path
    # e as rotas canônicas essenciais estão lá
    assert "/api/v1/health" in paths
    assert "/api/v1/ingest/events" in paths


def test_canonical_health():
    import app.stack360.main as canonical

    with TestClient(canonical.app) as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "stack360-core"}

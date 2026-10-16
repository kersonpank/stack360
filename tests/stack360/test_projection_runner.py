"""Testes com Postgres real (docker-compose.stack360.yml) — persistência do
bruto completo e auto-criação de DataSource."""
from datetime import datetime, timezone

from sqlalchemy import select

from app.stack360.models.data_source import DataSource
from app.stack360.models.raw_envelope import RawEnvelope
from app.stack360.projection.envelope import SourceEnvelope, persist_raw_envelope
from app.stack360.projection.runner import _resolve_or_create_source


def test_persist_raw_envelope_stores_full_content(db, make_workspace, make_source):
    ws = make_workspace()
    src = make_source(ws, key="mgsuporte")
    envelope = SourceEnvelope(
        source_key="mgsuporte",
        envelope_type="whatsapp.message",
        external_key="wa-1",
        content={"texto": "conteúdo completo, sem corte", "nested": {"a": 1}},
        captured_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    persist_raw_envelope(db, workspace_id=ws.id, data_source_id=src.id, envelope=envelope)

    row = db.execute(select(RawEnvelope).where(RawEnvelope.external_key == "wa-1")).scalar_one()
    assert row.content == {"texto": "conteúdo completo, sem corte", "nested": {"a": 1}}
    assert row.envelope_type == "whatsapp.message"


def test_persist_raw_envelope_idempotent(db, make_workspace, make_source):
    ws = make_workspace()
    src = make_source(ws, key="mgsuporte")
    envelope = SourceEnvelope(
        source_key="mgsuporte",
        envelope_type="whatsapp.message",
        external_key="wa-2",
        content={"texto": "x"},
        captured_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    persist_raw_envelope(db, workspace_id=ws.id, data_source_id=src.id, envelope=envelope)
    persist_raw_envelope(db, workspace_id=ws.id, data_source_id=src.id, envelope=envelope)  # rerun

    rows = db.execute(select(RawEnvelope).where(RawEnvelope.external_key == "wa-2")).scalars().all()
    assert len(rows) == 1


def test_resolve_existing_source_returned_as_is(db, make_workspace, make_source):
    ws = make_workspace()
    src = make_source(ws, key="mgsuporte")
    resolved = _resolve_or_create_source(db, ws, "mgsuporte", "whatsapp-legacy")
    assert resolved.id == src.id


def test_auto_creates_unknown_source(db, make_workspace, caplog):
    ws = make_workspace()
    created = _resolve_or_create_source(db, ws, "nova-instancia", "whatsapp-legacy")
    assert created.key == "nova-instancia"
    assert created.source_type == "whatsapp-legacy"

    row = db.execute(
        select(DataSource).where(DataSource.workspace_id == ws.id, DataSource.key == "nova-instancia")
    ).scalar_one()
    assert row.id == created.id
    assert "DataSource nova detectada" in caplog.text

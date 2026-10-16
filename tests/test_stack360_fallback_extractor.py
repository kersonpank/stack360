"""Testes do fallback — envelope de tipo desconhecido nunca é descartado,
mas também nunca carrega o conteúdo (já está em raw_envelopes)."""
from datetime import datetime, timezone

from app.stack360.projection.envelope import SourceEnvelope
from app.stack360.projection.extractors.fallback import extract_unmapped


def test_unmapped_generates_observation_with_field_names_only():
    envelope = SourceEnvelope(
        source_key="logre",
        envelope_type="logre.cotacao",
        external_key="cot-123",
        content={"cliente": "Empresa X", "valor": 1500.0, "cnpj": "12.345.678/0001-99"},
        captured_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    events = extract_unmapped(envelope)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "observation.recorded"
    assert event.data["key"] == "unmapped.logre.cotacao"
    assert event.data["value"] == {"unmapped_fields": ["cliente", "cnpj", "valor"]}
    # conteúdo real (nomes de cliente, valores, CNPJ) nunca aparece no evento
    serialized = str(event.data)
    assert "Empresa X" not in serialized
    assert "12.345.678" not in serialized
    assert event.data["source_ref"] == "logre:cot-123"


def test_unmapped_never_dropped_even_with_empty_content():
    envelope = SourceEnvelope(
        source_key="x", envelope_type="unknown.type", external_key="k1", content={}, captured_at=datetime.now(timezone.utc)
    )
    events = extract_unmapped(envelope)
    assert len(events) == 1

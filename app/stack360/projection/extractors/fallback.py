"""Fallback — quando nenhum extractor reconhece o `envelope_type`. Garante
"sem perda": o conteúdo já está seguro e completo em `stack360.raw_envelopes`
(ver `envelope.py`), então aqui só avisamos QUE existe algo não mapeado e
QUAIS campos — nunca o conteúdo em si (evita inflar o evento canônico e
duplicar dado que já está persistido)."""
from __future__ import annotations

from app.stack360.projection.envelope import SourceEnvelope
from app.stack360.schemas.envelope import StackEvent
from app.stack360.security.hashing import sha256_hex


def extract_unmapped(envelope: SourceEnvelope) -> list[StackEvent]:
    source_ref = f"{envelope.source_key}:{envelope.external_key}"
    event_id = sha256_hex(f"unmapped|{envelope.envelope_type}|{source_ref}")[:40]
    return [
        StackEvent(
            schema_version="1.0",
            event_id=event_id,
            event_type="observation.recorded",
            occurred_at=envelope.captured_at,
            data={
                "key": f"unmapped.{envelope.envelope_type}",
                "value": {"unmapped_fields": sorted(envelope.content.keys())},
                "confidence": None,
                "source_kind": "unmapped",
                "source_ref": source_ref,
            },
        )
    ]

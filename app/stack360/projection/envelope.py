"""Envelope padrão entre a camada 1 (reader) e a camada 2 (extractor) — o
mesmo shape serve pra qualquer fonte (WhatsApp, e-mail, Logre, planilha...).
A camada 3 (ingest_one/gateway/handlers/resolution) não muda — já é
source-agnostic por desenho.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.stack360.models.raw_envelope import RawEnvelope
from app.stack360.security.hashing import payload_hash


@dataclass(frozen=True)
class SourceEnvelope:
    """Saída de todo reader, entrada de todo extractor."""

    source_key: str        # bate com DataSource.key (ex.: "mgsuporte")
    envelope_type: str     # decide qual extractor roda (ex.: "whatsapp.message")
    external_key: str      # id na origem — idempotência/dedup/cursor de referência
    content: dict[str, Any]  # payload cru COMPLETO, sem corte — tudo que a origem deu
    captured_at: datetime    # quando a origem gerou (vira occurred_at do evento)
    source_cursor: Any = None  # valor de cursor monotônico da origem (ex.: loaded_at)


def persist_raw_envelope(
    db: Session, *, workspace_id: uuid.UUID, data_source_id: uuid.UUID, envelope: SourceEnvelope
) -> None:
    """Grava a cópia DURÁVEL e COMPLETA do envelope em `stack360.raw_envelopes`
    — insert-only, idempotente (ON CONFLICT DO NOTHING), sem filtro de campo
    sensível. Chamado pelo runner pra QUALQUER fonte, antes do extractor.
    """
    stmt = (
        pg_insert(RawEnvelope)
        .values(
            workspace_id=workspace_id,
            data_source_id=data_source_id,
            external_key=envelope.external_key,
            envelope_type=envelope.envelope_type,
            content=envelope.content,
            content_hash=payload_hash(envelope.content),
            fetched_at=envelope.captured_at,
        )
        .on_conflict_do_nothing(index_elements=["data_source_id", "external_key"])
    )
    db.execute(stmt)
    db.commit()

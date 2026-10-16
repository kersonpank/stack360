"""Reader — lê `raw_evolution_messages` (banco legado, só leitura) e devolve
`SourceEnvelope` padrão. Zero regra de negócio aqui — só leitura + shape."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterator, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.stack360.projection.envelope import SourceEnvelope

ENVELOPE_TYPE = "whatsapp.message"


def iter_envelopes(
    engine: Engine,
    *,
    since_cursor: Optional[datetime],
    overlap_hours: float = 3.0,
    batch_size: int = 500,
) -> Iterator[SourceEnvelope]:
    """Cursor monotônico por `loaded_at` (inserção na origem) — NUNCA por
    `message_datetime`/occurred_at do canônico (mensagem histórica entrando
    depois do cursor atual ficaria presa pra sempre)."""
    cursor = since_cursor
    if cursor is not None:
        cursor = cursor - timedelta(hours=overlap_hours)

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT external_message_id, source_account_id, instance_name,
                       whatsapp_message_id, remote_jid, participant, from_me,
                       push_name, message_type, message_datetime, loaded_at,
                       raw_message
                FROM raw_evolution_messages
                WHERE (:cursor IS NULL OR loaded_at > :cursor)
                ORDER BY loaded_at ASC
                LIMIT :limit
                """
            ),
            {"cursor": cursor, "limit": batch_size},
        ).mappings().all()

    for row in rows:
        yield SourceEnvelope(
            source_key=(row["instance_name"] or "unknown").lower(),
            envelope_type=ENVELOPE_TYPE,
            external_key=row["whatsapp_message_id"] or row["external_message_id"],
            content={
                "external_message_id": row["external_message_id"],
                "source_account_id": row["source_account_id"],
                "instance_name": row["instance_name"],
                "whatsapp_message_id": row["whatsapp_message_id"],
                "remote_jid": row["remote_jid"],
                "participant": row["participant"],
                "from_me": row["from_me"],
                "push_name": row["push_name"],
                "message_type": row["message_type"],
                "raw_message": row["raw_message"],
            },
            captured_at=row["message_datetime"] or row["loaded_at"] or datetime.now(),
            source_cursor=row["loaded_at"],
        )

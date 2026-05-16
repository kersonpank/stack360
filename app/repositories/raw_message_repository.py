from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session, defer

from app.models.raw_evolution_message import RawEvolutionMessage


class RawMessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def fetch_pending(
        self,
        limit: int = 100,
        source_account_id: Optional[str] = None,
    ) -> List[RawEvolutionMessage]:
        q = (
            self.db.query(RawEvolutionMessage)
            .options(defer(RawEvolutionMessage.raw_full))
            .filter(
                RawEvolutionMessage.normalized_at.is_(None),
                RawEvolutionMessage.external_message_id.isnot(None),
                RawEvolutionMessage.raw_message.isnot(None),
                RawEvolutionMessage.remote_jid.isnot(None),
                RawEvolutionMessage.message_timestamp > 0,
            )
        )
        if source_account_id:
            q = q.filter(RawEvolutionMessage.source_account_id == source_account_id)
        return q.order_by(RawEvolutionMessage.message_timestamp).limit(limit).all()

    def mark_normalized(self, write_db: Session, external_message_ids: List[str]) -> int:
        if not external_message_ids:
            return 0
        now = datetime.now(tz=timezone.utc)
        result = write_db.execute(
            text(
                "UPDATE raw_evolution_messages "
                "SET normalized_at = :now "
                "WHERE external_message_id = ANY(:ids)"
            ),
            {"now": now, "ids": external_message_ids},
        )
        return result.rowcount

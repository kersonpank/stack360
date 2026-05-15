from typing import List

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.source_account import SourceAccount


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_contact_id(self, contact_id: str) -> List[dict]:
        rows = (
            self.db.query(Conversation, SourceAccount.instance_name)
            .outerjoin(
                SourceAccount,
                Conversation.source_account_id == SourceAccount.source_account_id,
            )
            .filter(Conversation.contact_id == contact_id)
            .all()
        )
        result = []
        for conv, instance_name in rows:
            d = {c.name: getattr(conv, c.name) for c in conv.__table__.columns}
            d["instance_name"] = instance_name
            result.append(d)
        return result

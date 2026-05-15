from typing import List, Tuple

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_conversation_id(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0,
        order: str = "asc",
    ) -> Tuple[List[Message], int]:
        q = self.db.query(Message).filter(Message.conversation_id == conversation_id)
        total = q.count()
        order_fn = asc if order == "asc" else desc
        items = q.order_by(order_fn(Message.data_hora)).offset(offset).limit(limit).all()
        return items, total

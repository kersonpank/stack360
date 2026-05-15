from typing import List

from sqlalchemy.orm import Session

from app.models.timeline_event import TimelineEvent


class TimelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_contact_id(self, contact_id: str) -> List[TimelineEvent]:
        return (
            self.db.query(TimelineEvent)
            .filter(TimelineEvent.contact_id == contact_id)
            .order_by(TimelineEvent.data_hora.desc())
            .all()
        )

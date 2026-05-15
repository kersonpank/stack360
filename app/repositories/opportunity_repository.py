from typing import List

from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity


class OpportunityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_contact_id(self, contact_id: str) -> List[Opportunity]:
        return (
            self.db.query(Opportunity)
            .filter(Opportunity.contact_id == contact_id)
            .order_by(Opportunity.created_at.desc())
            .all()
        )

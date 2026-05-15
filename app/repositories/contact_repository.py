from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.contact import Contact


class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def search(self, q: str) -> List[Contact]:
        return (
            self.db.query(Contact)
            .filter(
                or_(
                    Contact.contact_id.ilike(f"%{q}%"),
                    Contact.telefone.ilike(f"%{q}%"),
                    Contact.nome_atual.ilike(f"%{q}%"),
                )
            )
            .all()
        )

    def get_by_id(self, contact_id: str) -> Optional[Contact]:
        return self.db.get(Contact, contact_id)

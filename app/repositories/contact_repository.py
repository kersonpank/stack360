from typing import List, Optional

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from app.models.contact import Contact


def _digits_only(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


SORT_FIELDS = {
    "name": Contact.nome_atual,
    "last_interaction": Contact.ultimo_contato_em,
    "messages": Contact.total_mensagens,
    "opportunity": Contact.score_oportunidade,
    "risk": Contact.score_risco,
    "created": Contact.created_at,
}


class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def search(self, q: str) -> List[Contact]:
        filters = [
            Contact.contact_id.ilike(f"%{q}%"),
            Contact.telefone.ilike(f"%{q}%"),
            Contact.nome_atual.ilike(f"%{q}%"),
        ]
        q_digits = _digits_only(q)
        if len(q_digits) >= 8:
            phone_suffix = q_digits[-8:]
            filters.extend(
                [
                    Contact.contact_id.ilike(f"%{phone_suffix}%"),
                    Contact.telefone.ilike(f"%{phone_suffix}%"),
                ]
            )

        return (
            self.db.query(Contact)
            .filter(or_(*filters))
            .all()
        )

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        q: Optional[str] = None,
        relationship_type: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        sort: str = "last_interaction",
        order: str = "desc",
    ) -> tuple[List[Contact], int]:
        query = self.db.query(Contact)

        if q:
            filters = [
                Contact.contact_id.ilike(f"%{q}%"),
                Contact.telefone.ilike(f"%{q}%"),
                Contact.nome_atual.ilike(f"%{q}%"),
            ]
            q_digits = _digits_only(q)
            if len(q_digits) >= 8:
                phone_suffix = q_digits[-8:]
                filters.extend(
                    [
                        Contact.contact_id.ilike(f"%{phone_suffix}%"),
                        Contact.telefone.ilike(f"%{phone_suffix}%"),
                    ]
                )
            query = query.filter(or_(*filters))
        if relationship_type:
            query = query.filter(Contact.tipo_relacionamento == relationship_type)
        if status:
            query = query.filter(Contact.status_relacionamento == status)
        if tag:
            query = query.filter(Contact.tags.any(tag))

        total = query.with_entities(func.count(Contact.contact_id)).scalar() or 0
        sort_column = SORT_FIELDS.get(sort, Contact.ultimo_contato_em)
        direction = asc if order == "asc" else desc

        items = (
            query.order_by(direction(sort_column).nullslast(), Contact.contact_id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_by_id(self, contact_id: str) -> Optional[Contact]:
        return self.db.get(Contact, contact_id)

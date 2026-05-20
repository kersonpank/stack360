from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.enrichment_state import EnrichmentState
from app.models.message import Message
from app.models.opportunity import Opportunity
from app.models.timeline_event import TimelineEvent


class EnrichmentRepository:
    def __init__(self, read_db: Session, write_db: Session):
        self.read_db = read_db
        self.write_db = write_db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_contacts_for_enrichment(self, limit: int = 100, contact_id: Optional[str] = None) -> List[Contact]:
        """
        Fetch contacts for enrichment.
        Priority: contacts with no enrichment_state first, then by recency.
        Guarantees coverage of all contacts regardless of ultimo_contato_em.
        """
        if contact_id:
            c = self.read_db.get(Contact, contact_id)
            return [c] if c else []

        rows = self.read_db.execute(
            text("""
                SELECT c.contact_id FROM contacts c
                LEFT JOIN enrichment_state es
                    ON es.entity_id = c.contact_id AND es.entity_type = 'contact'
                WHERE c.total_mensagens > 0
                ORDER BY
                    CASE WHEN es.entity_id IS NULL THEN 0 ELSE 1 END,
                    c.ultimo_contato_em DESC NULLS LAST
                LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()

        if not rows:
            return []

        contact_ids = [r[0] for r in rows]
        id_order = {cid: i for i, cid in enumerate(contact_ids)}
        contacts = self.read_db.query(Contact).filter(Contact.contact_id.in_(contact_ids)).all()
        contacts.sort(key=lambda c: id_order.get(c.contact_id, len(contact_ids)))
        return contacts

    def get_messages_for_contact(self, contact_id: str, last_n: int = 50, first_n: int = 10) -> List[Message]:
        """Return last N + first N messages for context building (deduplicated)."""
        last = (
            self.read_db.query(Message)
            .filter(Message.contact_id == contact_id, Message.texto.isnot(None))
            .order_by(Message.data_hora.desc().nullslast())
            .limit(last_n)
            .all()
        )
        first = (
            self.read_db.query(Message)
            .filter(Message.contact_id == contact_id, Message.texto.isnot(None))
            .order_by(Message.data_hora.asc().nullslast())
            .limit(first_n)
            .all()
        )
        seen = set()
        combined = []
        for m in first + last:
            if m.message_id not in seen:
                seen.add(m.message_id)
                combined.append(m)
        return combined

    def get_conversations_for_contact(self, contact_id: str) -> List[Conversation]:
        return (
            self.read_db.query(Conversation)
            .filter(Conversation.contact_id == contact_id)
            .all()
        )

    def get_source_accounts_for_contact(self, contact_id: str) -> List[str]:
        rows = (
            self.read_db.query(Message.source_account_id)
            .filter(Message.contact_id == contact_id, Message.source_account_id.isnot(None))
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    def get_enrichment_state(self, entity_type: str, entity_id: str) -> Optional[EnrichmentState]:
        return self.read_db.get(EnrichmentState, {"entity_type": entity_type, "entity_id": entity_id})

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def update_contact(self, contact_id: str, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(tz=timezone.utc)
        self.write_db.query(Contact).filter(Contact.contact_id == contact_id).update(
            data, synchronize_session=False
        )

    def update_conversation(self, conversation_id: str, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.now(tz=timezone.utc)
        self.write_db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).update(data, synchronize_session=False)

    def insert_timeline_event(self, event: Dict[str, Any]) -> None:
        """Insert only if no event of same tipo_evento exists for this contact."""
        exists = (
            self.write_db.query(TimelineEvent)
            .filter(
                TimelineEvent.contact_id == event["contact_id"],
                TimelineEvent.tipo_evento == event["tipo_evento"],
            )
            .first()
        )
        if not exists:
            self.write_db.add(TimelineEvent(**event))

    def count_timeline_events(self, contact_id: str) -> int:
        return (
            self.write_db.query(TimelineEvent)
            .filter(TimelineEvent.contact_id == contact_id)
            .count()
        )

    def insert_opportunity(self, opp: Dict[str, Any]) -> None:
        """Insert only if no nova/open opportunity of same tipo_oportunidade exists for this contact."""
        exists = (
            self.write_db.query(Opportunity)
            .filter(
                Opportunity.contact_id == opp["contact_id"],
                Opportunity.tipo_oportunidade == opp["tipo_oportunidade"],
                Opportunity.status.in_(["nova", "open"]),
            )
            .first()
        )
        if not exists:
            self.write_db.add(Opportunity(**opp))

    def upsert_enrichment_state(self, entity_type: str, entity_id: str, data: Dict[str, Any]) -> None:
        stmt = pg_insert(EnrichmentState).values(
            entity_type=entity_type,
            entity_id=entity_id,
            **data,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["entity_type", "entity_id"],
            set_={**data, "updated_at": datetime.now(tz=timezone.utc)},
        )
        self.write_db.execute(stmt)

    # ------------------------------------------------------------------
    # Status counts (for the enrichment-status endpoint)
    # ------------------------------------------------------------------

    def get_enrichment_counts(self) -> Dict[str, Any]:
        total_contacts = self.read_db.execute(text("SELECT COUNT(*) FROM contacts")).scalar()
        enriched = self.read_db.execute(
            text("SELECT COUNT(*) FROM enrichment_state WHERE entity_type = 'contact' AND status = 'done'")
        ).scalar()
        total_evidence = self.read_db.execute(text("SELECT COUNT(*) FROM contact_evidence")).scalar()
        total_timeline = self.read_db.execute(text("SELECT COUNT(*) FROM timeline_events")).scalar()
        total_opps = self.read_db.execute(text("SELECT COUNT(*) FROM opportunities")).scalar()
        open_opps = self.read_db.execute(
            text("SELECT COUNT(*) FROM opportunities WHERE status IN ('nova', 'open')")
        ).scalar()
        last_enriched = self.read_db.execute(
            text("SELECT MAX(last_enriched_at) FROM enrichment_state WHERE entity_type = 'contact'")
        ).scalar()
        by_tipo = self.read_db.execute(
            text(
                "SELECT tipo_relacionamento, COUNT(*) FROM contacts "
                "WHERE tipo_relacionamento IS NOT NULL "
                "GROUP BY tipo_relacionamento ORDER BY COUNT(*) DESC"
            )
        ).fetchall()
        top_tags = self.read_db.execute(
            text(
                "SELECT tag, COUNT(*) as cnt FROM contacts, unnest(tags) AS tag "
                "GROUP BY tag ORDER BY cnt DESC LIMIT 15"
            )
        ).fetchall()

        return {
            "total_contacts": total_contacts,
            "contacts_enriched": enriched,
            "contacts_pending": total_contacts - enriched,
            "total_evidence": total_evidence,
            "total_timeline_events": total_timeline,
            "total_opportunities": total_opps,
            "opportunities_open": open_opps,
            "last_enriched_at": last_enriched,
            "by_tipo_relacionamento": {row[0]: row[1] for row in by_tipo},
            "top_tags": [{"tag": row[0], "count": row[1]} for row in top_tags],
        }

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.contact_evidence import ContactEvidence
from app.models.opportunity import Opportunity
from app.models.stakeholder_action import StakeholderAction


class ActionRepository:
    def __init__(self, read_db: Session, write_db: Session):
        self.read_db = read_db
        self.write_db = write_db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_contacts_for_action_generation(
        self, limit: int = 100, contact_id: Optional[str] = None
    ) -> List[Contact]:
        if contact_id:
            c = self.read_db.get(Contact, contact_id)
            return [c] if c else []
        return (
            self.read_db.query(Contact)
            .filter(Contact.total_mensagens > 0)
            .order_by(Contact.score_oportunidade.desc().nullslast())
            .limit(limit)
            .all()
        )

    def get_open_opportunities_for_contact(self, contact_id: str) -> List[Opportunity]:
        return (
            self.read_db.query(Opportunity)
            .filter(
                Opportunity.contact_id == contact_id,
                Opportunity.status.in_(["nova", "open"]),
            )
            .all()
        )

    def get_evidence_types_for_contact(self, contact_id: str) -> List[str]:
        rows = (
            self.read_db.query(ContactEvidence.evidence_type)
            .filter(ContactEvidence.contact_id == contact_id)
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    def get_open_action(self, contact_id: str, action_type: str) -> Optional[StakeholderAction]:
        return (
            self.write_db.query(StakeholderAction)
            .filter(
                StakeholderAction.contact_id == contact_id,
                StakeholderAction.action_type == action_type,
                StakeholderAction.status.in_(["nova", "em_andamento"]),
            )
            .first()
        )

    def get_actions(
        self,
        status: Optional[str] = None,
        action_type: Optional[str] = None,
        min_priority: Optional[float] = None,
        contact_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        q = """
            SELECT
                sa.action_id, sa.contact_id, c.nome_atual AS stakeholder_name,
                sa.conversation_id, sa.opportunity_id, sa.action_type,
                sa.title, sa.description, sa.priority_score, sa.reason,
                sa.status, sa.assigned_to, sa.due_at, sa.source,
                sa.created_at, sa.updated_at
            FROM stakeholder_actions sa
            LEFT JOIN contacts c ON c.contact_id = sa.contact_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {}
        if status:
            q += " AND sa.status = :status"
            params["status"] = status
        if action_type:
            q += " AND sa.action_type = :action_type"
            params["action_type"] = action_type
        if min_priority is not None:
            q += " AND sa.priority_score >= :min_priority"
            params["min_priority"] = min_priority
        if contact_id:
            q += " AND sa.contact_id = :contact_id"
            params["contact_id"] = contact_id
        q += " ORDER BY sa.priority_score DESC NULLS LAST, sa.created_at DESC"
        q += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        rows = self.read_db.execute(text(q), params).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_summary(self) -> Dict[str, Any]:
        counts = self.read_db.execute(
            text("""
                SELECT status, COUNT(*) FROM stakeholder_actions GROUP BY status
            """)
        ).fetchall()
        by_type = self.read_db.execute(
            text("""
                SELECT action_type, COUNT(*) FROM stakeholder_actions GROUP BY action_type ORDER BY COUNT(*) DESC
            """)
        ).fetchall()
        top = self.read_db.execute(
            text("""
                SELECT
                    sa.action_id, sa.contact_id, c.nome_atual AS stakeholder_name,
                    sa.conversation_id, sa.opportunity_id, sa.action_type,
                    sa.title, sa.description, sa.priority_score, sa.reason,
                    sa.status, sa.assigned_to, sa.due_at, sa.source,
                    sa.created_at, sa.updated_at
                FROM stakeholder_actions sa
                LEFT JOIN contacts c ON c.contact_id = sa.contact_id
                WHERE sa.status IN ('nova', 'em_andamento')
                ORDER BY sa.priority_score DESC NULLS LAST
                LIMIT 10
            """)
        ).fetchall()

        status_map = {r[0]: r[1] for r in counts}
        total = sum(status_map.values())
        return {
            "total_actions": total,
            "novas": status_map.get("nova", 0),
            "em_andamento": status_map.get("em_andamento", 0),
            "concluidas": status_map.get("concluida", 0),
            "descartadas": status_map.get("descartada", 0),
            "by_action_type": {r[0]: r[1] for r in by_type},
            "top_priority": [dict(r._mapping) for r in top],
        }

    def get_action_system_status(self) -> Dict[str, Any]:
        total = self.read_db.execute(
            text("SELECT COUNT(*) FROM stakeholder_actions")
        ).scalar() or 0
        pending = self.read_db.execute(
            text("SELECT COUNT(*) FROM stakeholder_actions WHERE status IN ('nova', 'em_andamento')")
        ).scalar() or 0
        by_type = self.read_db.execute(
            text("SELECT action_type, COUNT(*) FROM stakeholder_actions GROUP BY action_type ORDER BY COUNT(*) DESC")
        ).fetchall()
        by_status = self.read_db.execute(
            text("SELECT status, COUNT(*) FROM stakeholder_actions GROUP BY status")
        ).fetchall()
        last_generated = self.read_db.execute(
            text("SELECT MAX(created_at) FROM stakeholder_actions")
        ).scalar()
        return {
            "total_actions": total,
            "pending_actions": pending,
            "actions_by_type": {r[0]: r[1] for r in by_type},
            "actions_by_status": {r[0]: r[1] for r in by_status},
            "last_generated_at": last_generated,
        }

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_action(self, data: Dict[str, Any]) -> str:
        """Insert or update action. Returns 'inserted' or 'updated'."""
        existing = self.get_open_action(data["contact_id"], data["action_type"])
        now = datetime.now(tz=timezone.utc)
        if existing:
            existing.priority_score = data.get("priority_score", existing.priority_score)
            existing.reason = data.get("reason", existing.reason)
            existing.payload = data.get("payload", existing.payload)
            existing.updated_at = now
            return "updated"
        action = StakeholderAction(
            **{k: v for k, v in data.items()},
            created_at=now,
            updated_at=now,
        )
        self.write_db.add(action)
        return "inserted"

    def update_status(self, action_id: int, status: str) -> Optional[StakeholderAction]:
        action = self.write_db.get(StakeholderAction, action_id)
        if not action:
            return None
        action.status = status
        action.updated_at = datetime.now(tz=timezone.utc)
        return action

    def get_actions_for_contact(self, contact_id: str) -> List[Dict[str, Any]]:
        rows = self.read_db.execute(
            text("""
                SELECT
                    sa.action_id, sa.contact_id, c.nome_atual AS stakeholder_name,
                    sa.conversation_id, sa.opportunity_id, sa.action_type,
                    sa.title, sa.description, sa.priority_score, sa.reason,
                    sa.status, sa.assigned_to, sa.due_at, sa.source,
                    sa.created_at, sa.updated_at
                FROM stakeholder_actions sa
                LEFT JOIN contacts c ON c.contact_id = sa.contact_id
                WHERE sa.contact_id = :contact_id
                ORDER BY sa.priority_score DESC NULLS LAST, sa.created_at DESC
            """),
            {"contact_id": contact_id},
        ).fetchall()
        return [dict(r._mapping) for r in rows]

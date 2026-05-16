from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session


class SystemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_normalization_status(self) -> Dict[str, Any]:
        raw_counts = self.db.execute(
            text("""
                SELECT
                    COUNT(*)                    AS total_raw,
                    COUNT(normalized_at)        AS total_normalized,
                    COUNT(*) - COUNT(normalized_at) AS total_pending
                FROM raw_evolution_messages
            """)
        ).fetchone()

        contacts = self.db.execute(text("SELECT COUNT(*) FROM contacts")).scalar()
        conversations = self.db.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
        messages = self.db.execute(text("SELECT COUNT(*) FROM messages")).scalar()

        by_source = self.db.execute(
            text("""
                SELECT
                    source_account_id,
                    instance_name,
                    COUNT(*)                        AS total_raw,
                    COUNT(normalized_at)            AS normalized,
                    COUNT(*) - COUNT(normalized_at) AS pending
                FROM raw_evolution_messages
                GROUP BY source_account_id, instance_name
                ORDER BY total_raw DESC
            """)
        ).fetchall()

        return {
            "total_raw": raw_counts[0],
            "total_raw_normalized": raw_counts[1],
            "total_raw_pending": raw_counts[2],
            "total_contacts": contacts,
            "total_conversations": conversations,
            "total_messages": messages,
            "by_source_account": [
                {
                    "source_account_id": row[0],
                    "instance_name": row[1],
                    "total_raw": row[2],
                    "normalized": row[3],
                    "pending": row[4],
                }
                for row in by_source
            ],
        }

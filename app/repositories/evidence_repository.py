from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Set

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.contact_evidence import ContactEvidence


def _get_existing_columns(engine) -> Set[str]:
    """Return column names that currently exist in contact_evidence."""
    inspector = inspect(engine)
    return {c["name"] for c in inspector.get_columns("contact_evidence")}


class EvidenceRepository:
    def __init__(self, read_db: Session, write_db: Session):
        self.read_db = read_db
        self.write_db = write_db
        # Cache existing columns once per repository instance
        self._existing_cols: Set[str] = _get_existing_columns(write_db.get_bind())

    def _filter_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Drop keys that don't (yet) exist as DB columns — schema-drift safety."""
        return {k: v for k, v in row.items() if k in self._existing_cols}

    def insert_deduped(self, rows: List[Dict[str, Any]]) -> int:
        """
        Insert evidence rows, skipping duplicates.
        Dedup key: (contact_id, evidence_type, evidence_value) — contact-level.
        In-memory set prevents duplicates within the same batch (same transaction);
        DB query prevents duplicates across runs.
        Returns number of rows inserted.
        """
        inserted = 0
        seen_in_batch: set = set()
        for row in rows:
            key = (row["contact_id"], row["evidence_type"], row["evidence_value"])
            if key in seen_in_batch:
                continue
            exists = self.write_db.execute(
                text("""
                    SELECT 1 FROM contact_evidence
                    WHERE contact_id = :cid
                      AND evidence_type = :etype
                      AND evidence_value = :evalue
                    LIMIT 1
                """),
                {
                    "cid": row["contact_id"],
                    "etype": row["evidence_type"],
                    "evalue": row["evidence_value"],
                },
            ).fetchone()
            if not exists:
                safe_row = self._filter_row(row)
                self.write_db.add(ContactEvidence(**safe_row))
                seen_in_batch.add(key)
                inserted += 1
        return inserted

    def get_by_contact_id(self, contact_id: str) -> List[ContactEvidence]:
        return (
            self.read_db.query(ContactEvidence)
            .filter(ContactEvidence.contact_id == contact_id)
            .order_by(ContactEvidence.created_at.desc())
            .all()
        )

    def get_contact_evidence_count(self, contact_id: str) -> int:
        return (
            self.read_db.query(ContactEvidence)
            .filter(ContactEvidence.contact_id == contact_id)
            .count()
        )

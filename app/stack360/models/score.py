from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, new_uuid, utcnow


class ScoreHistory(Stack360Base):
    """Métrica temporal. SEM score universal Stack360 ainda — só histórico por chave/fonte."""

    __tablename__ = "score_history"
    __table_args__ = (
        Index("ix_score_history_ws_person_key_time", "workspace_id", "person_id", "score_key", "calculated_at"),
        Index("ix_score_history_ws_company_key_time", "workspace_id", "company_id", "score_key", "calculated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experience_runs.id"), nullable=True
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    score_key: Mapped[str] = mapped_column(String, nullable=False)
    score_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    score_band: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reason_codes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    engine_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    engine_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, new_uuid, utcnow

_ZERO = "'00000000-0000-0000-0000-000000000000'::uuid"


class Observation(Stack360Base):
    """ALGO QUE APRENDEMOS. Append-only; nunca destrói evidência.

    Dedup SÓ do MESMO evento: (ingestion_event_id, person, company, key, value_hash).
    Evento NOVO com mesmo valor => NOVA observation (evidência temporal).
    """

    __tablename__ = "observations"
    __table_args__ = (
        Index("ix_observations_ws_person_key", "workspace_id", "person_id", "key"),
        Index("ix_observations_ws_company_key", "workspace_id", "company_id", "key"),
        Index(
            "uq_observations_same_event",
            text("ingestion_event_id"),
            text(f"coalesce(person_id, {_ZERO})"),
            text(f"coalesce(company_id, {_ZERO})"),
            text("key"),
            text("value_hash"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    ingestion_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_events.id"), nullable=False
    )
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    value_hash: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extractor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extractor_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

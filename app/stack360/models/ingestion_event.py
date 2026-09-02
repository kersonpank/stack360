from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, new_uuid, utcnow

# status
PENDING = "pending"
PROCESSED = "processed"
FAILED = "failed"
CONFLICT = "conflict"
SKIPPED = "skipped"


class IngestionEvent(Stack360Base):
    """O QUE CHEGOU AO STACK360 — bruto, durável, replayável.

    Persistido em TX própria (A). Nunca é apagado por rollback do domínio.
    Idempotência: UNIQUE(data_source_id, external_event_id).
    """

    __tablename__ = "ingestion_events"
    __table_args__ = (
        UniqueConstraint(
            "data_source_id", "external_event_id", name="uq_ingestion_events_source_extid"
        ),
        Index("ix_ingestion_events_workspace_status", "workspace_id", "status"),
        Index("ix_ingestion_events_event_type", "event_type"),
        Index("ix_ingestion_events_received_at", "received_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    external_event_id: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=PENDING)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

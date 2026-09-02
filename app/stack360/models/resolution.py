from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, new_uuid, utcnow

CASE_TYPES = (
    "identity_conflict",
    "unresolved_identity",
    "possible_duplicate_person",
    "possible_duplicate_company",
    "company_conflict",
    "contradictory_observation",
    "ingestion_error",
    "event_id_conflict",  # H2: mesmo (source, external_event_id) com payload/contrato incompatível
)
CASE_STATUSES = (
    "open",
    "investigating",
    "recommendation_ready",
    "awaiting_review",
    "resolved",
    "dismissed",
)
OPEN_STATUSES = ("open", "investigating", "recommendation_ready", "awaiting_review")


class ResolutionCase(Stack360Base):
    """Conflito/ambiguidade rastreável. IA = investigador/recomendador;
    Stack360/policy/humano = autoridade de resolução. Sem auto-merge nesta versão.
    """

    __tablename__ = "resolution_cases"
    __table_args__ = (
        Index("ix_resolution_cases_ws_status", "workspace_id", "status"),
        Index("ix_resolution_cases_ws_case_type", "workspace_id", "case_type"),
        Index("ix_resolution_cases_ws_severity", "workspace_id", "severity"),
        Index("ix_resolution_cases_ingestion_event_id", "ingestion_event_id"),
        # dedup: 1 caso aberto por (workspace, case_type, ingestion_event)
        Index(
            "uq_resolution_cases_open_per_event",
            "workspace_id",
            "case_type",
            "ingestion_event_id",
            unique=True,
            postgresql_where=text("status NOT IN ('resolved','dismissed')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    ingestion_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_events.id"), nullable=True
    )
    case_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    severity: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    subject_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_action: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolution_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    resolved_by_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # rule|human|agent
    resolved_by_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ResolutionRecommendation(Stack360Base):
    """Recomendação registrada por regra/humano/agente. NUNCA chain-of-thought —
    só conclusão + evidência estruturada + confidence + justificativa curta.
    NÃO executa merge/alteração de identidade.
    """

    __tablename__ = "resolution_recommendations"
    __table_args__ = (Index("ix_resolution_recommendations_case_id", "resolution_case_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    resolution_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resolution_cases.id"), nullable=False
    )
    recommended_action: Mapped[str] = mapped_column(String, nullable=False)
    candidate_entity_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

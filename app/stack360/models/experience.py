from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, TimestampMixin, new_uuid, utcnow


class Experience(Stack360Base):
    """diagnóstico / quiz / simulador / calculadora / form interativo.

    NÃO é form builder. Precisa ser registrada (CLI) antes de receber runs.
    """

    __tablename__ = "experiences"
    __table_args__ = (
        UniqueConstraint("workspace_id", "key", "version", name="uq_experiences_ws_key_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    key: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    experience_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ExperienceRun(Stack360Base, TimestampMixin):
    __tablename__ = "experience_runs"
    __table_args__ = (
        UniqueConstraint(
            "data_source_id", "experience_id", "external_run_id",
            name="uq_experience_runs_source_exp_run",
        ),
        Index("ix_experience_runs_ws_experience", "workspace_id", "experience_id"),
        Index("ix_experience_runs_ws_person", "workspace_id", "person_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    experience_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiences.id"), nullable=False
    )
    external_run_id: Mapped[str] = mapped_column(String, nullable=False)
    visitor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    person_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=True
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="started")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    landing_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class Answer(Stack360Base):
    """Append-only. Resposta alterada = novo fato. Projeção 'última' via query."""

    __tablename__ = "answers"
    __table_args__ = (Index("ix_answers_run_question_time", "run_id", "question_key", "answered_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experience_runs.id"), nullable=False
    )
    question_key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    answer_hash: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_events.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Result(Stack360Base):
    """Append-only / versionado. Saída de motor/experiência."""

    __tablename__ = "results"
    __table_args__ = (Index("ix_results_run_type_time", "run_id", "result_type", "calculated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experience_runs.id"), nullable=False
    )
    result_type: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score_band: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dimensions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    result: Mapped[Any] = mapped_column(JSONB, nullable=False)
    engine_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    engine_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    result_hash: Mapped[str] = mapped_column(String, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_events.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

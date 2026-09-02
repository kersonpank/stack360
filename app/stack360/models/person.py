from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, TimestampMixin, new_uuid, utcnow

# Identidades FORTES globais no v1 = SÓ estas. Todo o resto é source-scoped.
STRONG_GLOBAL_TYPES = ("email", "phone")


class Person(Stack360Base, TimestampMixin):
    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    canonical_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class PersonIdentity(Stack360Base):
    __tablename__ = "person_identities"
    __table_args__ = (
        # forte global: email/phone unívocos entre todo o Stack360
        Index(
            "uq_person_identities_strong_global",
            "identity_type",
            "value_hash",
            unique=True,
            postgresql_where=text("identity_type IN ('email','phone')"),
        ),
        # source-scoped: qualquer outro tipo, unívoco por data_source
        Index(
            "uq_person_identities_source_scoped",
            "data_source_id",
            "identity_type",
            "value_hash",
            unique=True,
            postgresql_where=text("identity_type NOT IN ('email','phone')"),
        ),
        Index("ix_person_identities_person_id", "person_id"),
        Index("ix_person_identities_value_hash", "value_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), nullable=False
    )
    data_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True
    )
    identity_type: Mapped[str] = mapped_column(String, nullable=False)
    value_normalized: Mapped[str] = mapped_column(String, nullable=False)
    value_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class WorkspacePerson(Stack360Base):
    __tablename__ = "workspace_people"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), primary_key=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("people.id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

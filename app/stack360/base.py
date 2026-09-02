"""Base declarativa própria do Stack360, isolada no schema ``stack360``.

NÃO reutiliza ``app.core.database.Base`` (legado). Assim o autogenerate do
Alembic legado nunca enxerga estas tabelas e vice-versa.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.stack360 import SCHEMA

_NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Stack360Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA, naming_convention=_NAMING)


def new_uuid() -> uuid.UUID:
    """UUID gerado pela APLICAÇÃO — a migration não depende de pgcrypto."""
    return uuid.uuid4()


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

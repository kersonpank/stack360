from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, TimestampMixin, new_uuid


class Workspace(Stack360Base, TimestampMixin):
    """O NEGÓCIO DONO DOS DADOS (ex.: Stack360 Empresas).

    NÃO confundir com ``companies`` (empresa prospect/cliente).
    """

    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")

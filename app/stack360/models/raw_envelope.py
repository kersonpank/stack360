from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, new_uuid, utcnow


class RawEnvelope(Stack360Base):
    """Cópia DURÁVEL e COMPLETA de tudo que qualquer reader leu de qualquer
    fonte — conteúdo sem corte, sem filtro de campo sensível (ex.: cabeçalhos
    de e-mail inteiros). Só inserção, nunca atualizada.

    Acesso restrito: NÃO exposta por nenhuma rota REST — só o motor
    (extractors) e auditoria direta no banco. Eventos canônicos
    (Observation/Interaction) carregam só uma referência (`data_source.key`
    + `external_key`), nunca o conteúdo em si — ver `app/stack360/projection/`.

    Desacopla o Stack360 de depender da fonte original continuar viva: uma
    vez lido, o bruto fica aqui pra sempre (reprocessável quando as regras
    de extração melhorarem, sem pedir nada de novo à origem).
    """

    __tablename__ = "raw_envelopes"
    __table_args__ = (
        UniqueConstraint("data_source_id", "external_key", name="uq_raw_envelopes_source_extkey"),
        Index("ix_raw_envelopes_ws_source", "workspace_id", "data_source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    external_key: Mapped[str] = mapped_column(String, nullable=False)
    envelope_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

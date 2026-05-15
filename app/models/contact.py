from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[str] = mapped_column(String, primary_key=True)
    telefone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nome_atual: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tipo_relacionamento: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status_relacionamento: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    primeiro_contato_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_contato_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_mensagens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_oportunidade: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    score_risco: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    resumo_geral: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

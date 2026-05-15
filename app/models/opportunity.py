from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    opportunity_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contact_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("contacts.contact_id"), nullable=True
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.conversation_id"), nullable=True
    )
    origem_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tipo_oportunidade: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    proxima_acao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsavel: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    espo_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

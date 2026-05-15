from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String, primary_key=True)
    external_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("conversations.conversation_id"), nullable=True
    )
    contact_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("contacts.contact_id"), nullable=True
    )
    source_account_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("source_accounts.source_account_id"), nullable=True
    )
    data_hora: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_timestamp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    remote_jid: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    canonical_jid: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    enviada_por_mim: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    nome_contato: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tipo_mensagem: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_message: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

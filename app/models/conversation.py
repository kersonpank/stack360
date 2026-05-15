from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String, primary_key=True)
    contact_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("contacts.contact_id"), nullable=True
    )
    source_account_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("source_accounts.source_account_id"), nullable=True
    )
    remote_jid: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tipo_chat: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    primeira_mensagem_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ultima_mensagem_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_mensagens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assunto_principal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resumo_conversa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_conversa: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

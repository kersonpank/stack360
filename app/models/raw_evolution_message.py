from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RawEvolutionMessage(Base):
    __tablename__ = "raw_evolution_messages"

    external_message_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_account_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evolution_instance_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instance_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evolution_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    whatsapp_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    remote_jid: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    from_me: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    push_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    message_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    message_timestamp: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_key: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    raw_message: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    raw_full: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    loaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    normalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chatwoot_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    chatwoot_inbox_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    chatwoot_conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    participant: Mapped[Optional[str]] = mapped_column(String, nullable=True)

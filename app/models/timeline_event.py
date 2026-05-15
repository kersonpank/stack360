from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contact_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("contacts.contact_id"), nullable=True
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    data_hora: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tipo_evento: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    titulo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importancia: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContactEvidence(Base):
    __tablename__ = "contact_evidence"

    evidence_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String, nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    evidence_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0)
    source: Mapped[Optional[str]] = mapped_column(String, default="rules")
    payload: Mapped[Optional[Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

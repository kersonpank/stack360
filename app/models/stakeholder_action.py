from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StakeholderAction(Base):
    __tablename__ = "stakeholder_actions"

    action_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String, nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    opportunity_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority_score: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="nova")
    assigned_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String, default="rules")
    payload: Mapped[Optional[Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

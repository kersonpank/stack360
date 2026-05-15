from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourceAccount(Base):
    __tablename__ = "source_accounts"

    source_account_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_system: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evolution_instance_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    instance_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

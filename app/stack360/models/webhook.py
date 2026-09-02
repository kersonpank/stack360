from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.stack360.base import Stack360Base, TimestampMixin, new_uuid


class WebhookEndpoint(Stack360Base, TimestampMixin):
    """Config de webhook inbound. Pertence a EXATAMENTE uma data_source + mesmo workspace.

    Secret cifrado at-rest (AES-GCM, master key STACK360_WEBHOOK_SECRET_KEY).
    NUNCA plaintext, NUNCA hash irreversível p/ validar HMAC.
    """

    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False
    )
    source_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    secret_encrypted: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    secret_key_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    signature_header: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    signature_scheme: Mapped[str] = mapped_column(String, nullable=False, default="hmac-sha256")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

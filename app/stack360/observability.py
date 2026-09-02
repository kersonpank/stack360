"""Logging estruturado. NUNCA loga API keys, secrets, nem payload completo com PII."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from app.stack360.schemas.envelope import StackEvent

_logger = logging.getLogger("stack360")
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_h)
    _logger.setLevel(logging.INFO)


def log_event(
    event: StackEvent,
    ingestion_event_id: uuid.UUID,
    status: str,
    auth: Any,
    *,
    entities: Optional[dict] = None,
    error_code: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    rec = {
        "evt": "ingestion",
        "event_id": event.event_id,
        "ingestion_event_id": str(ingestion_event_id),
        "workspace": getattr(auth, "workspace_slug", None) or str(getattr(auth, "workspace_id", "")),
        "source": getattr(auth, "data_source_key", None),
        "event_type": event.event_type,
        "status": status,
        # top-level keys do payload — nunca o payload inteiro
        "payload_keys": sorted(event.data.keys()) if isinstance(event.data, dict) else [],
    }
    ent = entities or {}
    for k in ("person_id", "company_id", "run_id"):
        if ent.get(k):
            rec[k] = ent[k]
    if error_code:
        rec["error_code"] = error_code
    if extra:
        rec.update(extra)
    _logger.info(json.dumps(rec, default=str))

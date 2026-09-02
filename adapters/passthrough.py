"""Adapter genérico: o corpo cru vira o ``data`` de um StackEvent.

``mapping`` (de ``webhook_endpoints.mapping``) pode conter:
  - ``event_type``        : event_type fixo (default "webhook.received")
  - ``event_id_path``     : caminho pontilhado no JSON p/ o id externo
  - ``occurred_at_path``  : caminho pontilhado p/ o timestamp
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.stack360.schemas.envelope import StackEvent
from app.stack360.security.hashing import sha256_hex


def _dig(obj, path: str):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def passthrough_adapter(body: bytes, mapping: dict, source_key: str) -> StackEvent:
    try:
        parsed = json.loads(body.decode("utf-8") or "{}")
    except Exception:
        parsed = {"_raw": body.decode("utf-8", "replace")}

    event_type = mapping.get("event_type") or "webhook.received"

    ext_id = None
    if mapping.get("event_id_path"):
        ext_id = _dig(parsed, mapping["event_id_path"])
    if not ext_id:
        ext_id = sha256_hex(source_key.encode() + b":" + body)

    occurred = None
    if mapping.get("occurred_at_path"):
        raw_ts = _dig(parsed, mapping["occurred_at_path"])
        if raw_ts:
            try:
                occurred = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            except Exception:
                occurred = None
    if occurred is None:
        occurred = datetime.now(tz=timezone.utc)

    return StackEvent(
        schema_version="1.0",
        event_id=str(ext_id),
        event_type=event_type,
        occurred_at=occurred,
        data=parsed if isinstance(parsed, dict) else {"value": parsed},
    )

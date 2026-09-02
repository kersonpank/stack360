from __future__ import annotations

from app.stack360.ingestion.handlers import HandlerContext, register
from app.stack360.ingestion.handlers._common import resolve_company_from_event
from app.stack360.models.observation import Observation
from app.stack360.security.hashing import canonical_json, sha256_hex


@register(family="company", exact="company.observed")
def handle_company(ctx: HandlerContext) -> None:
    company_id = resolve_company_from_event(ctx)
    data = ctx.event.data if isinstance(ctx.event.data, dict) else {}
    key = data.get("key")
    if company_id and key:
        vh = sha256_hex(f"{key}:{canonical_json(data.get('value'))}")
        ctx.db.add(
            Observation(
                workspace_id=ctx.workspace_id,
                data_source_id=ctx.data_source_id,
                ingestion_event_id=ctx.ingestion_event.id,
                company_id=company_id,
                key=key,
                value=data.get("value") if data.get("value") is not None else {},
                value_hash=vh,
                confidence=data.get("confidence"),
                source_kind=data.get("source_kind") or "declared",
                observed_at=ctx.event.occurred_at,
            )
        )
        ctx.db.flush()

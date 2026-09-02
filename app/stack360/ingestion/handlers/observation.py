from __future__ import annotations

from app.stack360.ingestion.handlers import HandlerContext, register
from app.stack360.ingestion.handlers._common import (
    resolve_company_from_event,
    resolve_person_from_event,
)
from app.stack360.models.observation import Observation
from app.stack360.security.hashing import canonical_json, sha256_hex


@register(family="observation", exact="observation.recorded")
def handle_observation(ctx: HandlerContext) -> None:
    person = resolve_person_from_event(ctx)
    company_id = resolve_company_from_event(ctx)

    data = ctx.event.data if isinstance(ctx.event.data, dict) else {}
    key = data.get("key")
    if not key:
        # sem key não há observação — não falha o evento
        return
    value = data.get("value")
    vh = sha256_hex(f"{key}:{canonical_json(value)}")

    obs = Observation(
        workspace_id=ctx.workspace_id,
        data_source_id=ctx.data_source_id,
        ingestion_event_id=ctx.ingestion_event.id,
        person_id=person.person_id,
        company_id=company_id,
        key=key,
        value=value if value is not None else {},
        value_hash=vh,
        confidence=data.get("confidence"),
        source_kind=data.get("source_kind") or "declared",
        source_ref=data.get("source_ref"),
        extractor=data.get("extractor"),
        extractor_version=data.get("extractor_version"),
        observed_at=ctx.event.occurred_at,
    )
    ctx.db.add(obs)
    ctx.db.flush()
    ctx.entities.setdefault("observation_ids", []).append(str(obs.id))

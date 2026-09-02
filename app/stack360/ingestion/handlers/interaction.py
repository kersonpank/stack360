from __future__ import annotations

from app.stack360.ingestion.handlers import HandlerContext, register
from app.stack360.ingestion.handlers._common import (
    link_person_company,
    resolve_company_from_event,
    resolve_person_from_event,
)
from app.stack360.models.interaction import Interaction


@register(family="interaction")
def handle_interaction(ctx: HandlerContext) -> None:
    person = resolve_person_from_event(ctx)
    company_id = resolve_company_from_event(ctx)
    link_person_company(ctx, person.person_id, company_id)

    e = ctx.event
    context = e.context
    data = e.data if isinstance(e.data, dict) else {}
    inter = Interaction(
        workspace_id=ctx.workspace_id,
        data_source_id=ctx.data_source_id,
        ingestion_event_id=ctx.ingestion_event.id,
        person_id=person.person_id,
        company_id=company_id,
        interaction_type=e.event_type.split(".", 1)[1] if "." in e.event_type else e.event_type,
        channel=(context.channel if context else None) or data.get("channel"),
        direction=(context.direction if context else None) or data.get("direction"),
        external_interaction_id=data.get("external_interaction_id")
        or (context.external_run_id if context else None),
        occurred_at=e.occurred_at,
        meta=data,
    )
    ctx.db.add(inter)
    ctx.db.flush()
    ctx.entities["interaction_id"] = str(inter.id)

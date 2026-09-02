from __future__ import annotations

from app.stack360.ingestion.handlers import HandlerContext, register
from app.stack360.ingestion.handlers._common import (
    link_person_company,
    resolve_company_from_event,
    resolve_person_from_event,
)


@register(family="identity", exact="identity.observed")
def handle_identity(ctx: HandlerContext) -> None:
    res = resolve_person_from_event(ctx)
    company_id = resolve_company_from_event(ctx)
    link_person_company(ctx, res.person_id, company_id)
    ctx.entities["identities_linked"] = len(res.normalized)
    if res.invalid:
        ctx.entities["identities_invalid"] = len(res.invalid)

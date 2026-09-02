from __future__ import annotations

from app.stack360.ingestion.handlers import HandlerContext, register
from app.stack360.ingestion.handlers._common import (
    resolve_company_from_event,
    resolve_person_from_event,
)
from app.stack360.models.score import ScoreHistory


@register(family="score", exact="score.calculated")
def handle_score(ctx: HandlerContext) -> None:
    person = resolve_person_from_event(ctx)
    company_id = resolve_company_from_event(ctx)
    data = ctx.event.data if isinstance(ctx.event.data, dict) else {}

    if data.get("score_key") is None or data.get("score_value") is None:
        return

    sh = ScoreHistory(
        workspace_id=ctx.workspace_id,
        data_source_id=ctx.data_source_id,
        person_id=person.person_id,
        company_id=company_id,
        run_id=None,
        score_key=str(data["score_key"]),
        score_value=data["score_value"],
        score_band=data.get("score_band"),
        reason_codes=data.get("reason_codes"),
        engine_name=data.get("engine_name"),
        engine_version=data.get("engine_version"),
        source_ref=data.get("source_ref"),
        calculated_at=ctx.event.occurred_at,
    )
    ctx.db.add(sh)
    ctx.db.flush()
    ctx.entities["score_history_id"] = str(sh.id)

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.base import utcnow
from app.stack360.ingestion.handlers import HandlerContext, register
from app.stack360.ingestion.handlers._common import (
    link_person_company,
    resolve_company_from_event,
)
from app.stack360.models.experience import Answer, Experience, ExperienceRun, Result
from app.stack360.resolution.identity import link_identities_to_person, resolve_person
from app.stack360.schemas.envelope import IdentityIn
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.security.hashing import canonical_json, sha256_hex


def _require_experience(ctx: HandlerContext) -> Experience:
    c = ctx.event.context
    key = c.experience_key if c else None
    version = str(c.experience_version) if (c and c.experience_version is not None) else None
    if not key or not version:
        raise Stack360Error(
            ErrorCode.VALIDATION_ERROR,
            "context.experience_key e context.experience_version são obrigatórios para eventos experience.*",
        )
    exp = ctx.db.execute(
        select(Experience).where(
            Experience.workspace_id == ctx.workspace_id,
            Experience.key == key,
            Experience.version == version,
        )
    ).scalar_one_or_none()
    if exp is None:
        raise Stack360Error(
            ErrorCode.EXPERIENCE_NOT_FOUND,
            f"experience '{key}' v{version} não registrada — registre via "
            f"`admin create-experience` antes de enviar runs",
            {"experience_key": key, "experience_version": version},
        )
    return exp


def _get_or_create_run(ctx: HandlerContext, exp: Experience) -> ExperienceRun:
    c = ctx.event.context
    external_run_id = (c.external_run_id if c else None) or ctx.event.data.get("external_run_id")
    if not external_run_id:
        raise Stack360Error(
            ErrorCode.VALIDATION_ERROR, "external_run_id obrigatório (context.external_run_id ou data.external_run_id)"
        )
    run = ctx.db.execute(
        select(ExperienceRun).where(
            ExperienceRun.data_source_id == ctx.data_source_id,
            ExperienceRun.experience_id == exp.id,
            ExperienceRun.external_run_id == external_run_id,
        )
    ).scalar_one_or_none()
    if run is not None:
        return run
    attr = ctx.event.attribution
    run = ExperienceRun(
        workspace_id=ctx.workspace_id,
        data_source_id=ctx.data_source_id,
        experience_id=exp.id,
        external_run_id=external_run_id,
        visitor_id=(c.visitor_id if c else None) or ctx.event.data.get("visitor_id"),
        status="started",
        started_at=ctx.event.occurred_at,
        last_activity_at=ctx.event.occurred_at,
        utm_source=attr.utm_source if attr else None,
        utm_medium=attr.utm_medium if attr else None,
        utm_campaign=attr.utm_campaign if attr else None,
        utm_content=attr.utm_content if attr else None,
        utm_term=attr.utm_term if attr else None,
        referrer=attr.referrer if attr else None,
        landing_url=attr.landing_url if attr else None,
    )
    ctx.db.add(run)
    ctx.db.flush()
    return run


def _touch(run: ExperienceRun, ctx: HandlerContext) -> None:
    run.last_activity_at = ctx.event.occurred_at


@register(family="experience")
def handle_experience(ctx: HandlerContext) -> None:
    action = ctx.event.event_type.split(".", 1)[1] if "." in ctx.event.event_type else ""
    exp = _require_experience(ctx)
    run = _get_or_create_run(ctx, exp)
    ctx.entities["run_id"] = str(run.id)
    ctx.entities["experience_id"] = str(exp.id)

    data = ctx.event.data if isinstance(ctx.event.data, dict) else {}

    if action == "run_started":
        _touch(run, ctx)
        return

    if action == "answer_recorded":
        qkey = data.get("question_key")
        if not qkey:
            raise Stack360Error(ErrorCode.VALIDATION_ERROR, "data.question_key obrigatório")
        value = data.get("value")
        ans = Answer(
            workspace_id=ctx.workspace_id,
            run_id=run.id,
            question_key=str(qkey),
            value=value if value is not None else {},
            answer_hash=sha256_hex(f"{qkey}:{canonical_json(value)}"),
            context=data.get("context"),
            answered_at=ctx.event.occurred_at,
            ingestion_event_id=ctx.ingestion_event.id,
        )
        ctx.db.add(ans)
        _touch(run, ctx)
        ctx.db.flush()
        ctx.entities["answer_id"] = str(ans.id)
        return

    if action == "identity_captured":
        idents: list[IdentityIn] = list(ctx.event.subject.identities) if ctx.event.subject else []
        if run.person_id is None and idents:
            res = resolve_person(
                ctx.db,
                workspace_id=ctx.workspace_id,
                data_source_id=ctx.data_source_id,
                identities_in=idents,
                name_hint=data.get("name"),
            )
            run.person_id = res.person_id
        elif run.person_id is not None and idents:
            link_identities_to_person(
                ctx.db,
                workspace_id=ctx.workspace_id,
                data_source_id=ctx.data_source_id,
                person_id=run.person_id,
                identities_in=idents,
            )
        company_id = resolve_company_from_event(ctx)
        if company_id and run.company_id is None:
            run.company_id = company_id
        link_person_company(ctx, run.person_id, company_id or run.company_id)
        if run.person_id:
            ctx.entities["person_id"] = str(run.person_id)
        _touch(run, ctx)
        ctx.db.flush()
        return

    if action == "run_completed":
        run.status = "completed"
        run.completed_at = ctx.event.occurred_at
        _touch(run, ctx)
        result_data = data.get("result")
        if result_data is not None or data.get("score") is not None:
            payload = result_data if isinstance(result_data, dict) else {"value": result_data}
            res = Result(
                workspace_id=ctx.workspace_id,
                run_id=run.id,
                result_type=data.get("result_type") or "diagnostic",
                score=data.get("score"),
                verdict=data.get("verdict"),
                score_band=data.get("score_band"),
                dimensions=data.get("dimensions"),
                result=payload,
                engine_name=data.get("engine_name"),
                engine_version=data.get("engine_version"),
                result_hash=sha256_hex(canonical_json({"r": payload, "s": data.get("score")})),
                calculated_at=ctx.event.occurred_at,
                ingestion_event_id=ctx.ingestion_event.id,
            )
            ctx.db.add(res)
            ctx.db.flush()
            ctx.entities["result_id"] = str(res.id)
        ctx.db.flush()
        return

    # ação desconhecida da família experience — apenas garante o run
    _touch(run, ctx)

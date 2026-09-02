from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.api.deps import db_session, require_read
from app.stack360.api.errors import Stack360Route
from app.stack360.auth import AuthContext
from app.stack360.models.experience import Answer, Experience, ExperienceRun, Result
from app.stack360.schemas.errors import ErrorCode, Stack360Error

router = APIRouter(tags=["Experiences"], route_class=Stack360Route)


def _exp_dict(e: Experience) -> dict:
    return {
        "id": str(e.id),
        "key": e.key,
        "version": e.version,
        "name": e.name,
        "experience_type": e.experience_type,
        "status": e.status,
    }


def _run_dict(r: ExperienceRun) -> dict:
    return {
        "id": str(r.id),
        "experience_id": str(r.experience_id),
        "external_run_id": r.external_run_id,
        "visitor_id": r.visitor_id,
        "person_id": str(r.person_id) if r.person_id else None,
        "company_id": str(r.company_id) if r.company_id else None,
        "status": r.status,
        "started_at": r.started_at,
        "completed_at": r.completed_at,
        "utm": {
            "source": r.utm_source,
            "medium": r.utm_medium,
            "campaign": r.utm_campaign,
            "content": r.utm_content,
            "term": r.utm_term,
        },
        "referrer": r.referrer,
        "landing_url": r.landing_url,
    }


@router.get("/experiences")
def list_experiences(ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    rows = db.execute(
        select(Experience).where(Experience.workspace_id == ctx.workspace_id).order_by(Experience.key, Experience.version)
    ).scalars().all()
    return {"items": [_exp_dict(e) for e in rows]}


@router.get("/experiences/{experience_id}/runs")
def list_runs(experience_id: uuid.UUID, ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    exp = db.get(Experience, experience_id)
    if exp is None or exp.workspace_id != ctx.workspace_id:
        raise Stack360Error(ErrorCode.NOT_FOUND, "experience não encontrada")
    rows = db.execute(
        select(ExperienceRun)
        .where(ExperienceRun.experience_id == experience_id, ExperienceRun.workspace_id == ctx.workspace_id)
        .order_by(ExperienceRun.created_at.desc())
        .limit(200)
    ).scalars().all()
    return {"experience": _exp_dict(exp), "items": [_run_dict(r) for r in rows]}


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, ctx: AuthContext = Depends(require_read), db: Session = Depends(db_session)):
    run = db.get(ExperienceRun, run_id)
    if run is None or run.workspace_id != ctx.workspace_id:
        raise Stack360Error(ErrorCode.NOT_FOUND, "run não encontrada")
    # última resposta por question_key
    answers = db.execute(
        select(Answer).where(Answer.run_id == run_id).order_by(Answer.question_key, Answer.answered_at.desc())
    ).scalars().all()
    latest: dict[str, Answer] = {}
    for a in answers:
        latest.setdefault(a.question_key, a)
    results = db.execute(
        select(Result).where(Result.run_id == run_id).order_by(Result.calculated_at.desc())
    ).scalars().all()
    return {
        "run": _run_dict(run),
        "answers_latest": [
            {"question_key": k, "value": a.value, "answered_at": a.answered_at} for k, a in latest.items()
        ],
        "answers_count": len(answers),
        "results": [
            {
                "result_type": r.result_type,
                "score": float(r.score) if r.score is not None else None,
                "verdict": r.verdict,
                "score_band": r.score_band,
                "dimensions": r.dimensions,
                "result": r.result,
                "engine_name": r.engine_name,
                "engine_version": r.engine_version,
                "calculated_at": r.calculated_at,
            }
            for r in results
        ],
    }

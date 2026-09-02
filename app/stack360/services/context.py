"""Assembla o CONTEXT de uma Person/Company — estrutura previsível p/ agentes.

Uma única implementação, reusada por REST e MCP (zero divergência de regra).
Workspace isolation SEMPRE aplicado. Sem histórico infinito por padrão.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.config import get_settings
from app.stack360.models.company import Company, PersonCompanyRelationship, WorkspaceCompany
from app.stack360.models.data_source import DataSource
from app.stack360.models.experience import Experience, ExperienceRun, Result
from app.stack360.models.interaction import Interaction
from app.stack360.models.observation import Observation
from app.stack360.models.person import Person, PersonIdentity, WorkspacePerson
from app.stack360.models.score import ScoreHistory
from app.stack360.schemas.errors import ErrorCode, Stack360Error

_SECTIONS = (
    "identities",
    "companies",
    "recent_interactions",
    "observations",
    "experience_runs",
    "results",
    "scores",
)


def _src_keys(db: Session) -> dict[uuid.UUID, str]:
    return {r.id: r.key for r in db.execute(select(DataSource)).scalars()}


def _wanted(include: Optional[str]) -> set[str]:
    if not include:
        return set(_SECTIONS)
    return {s.strip() for s in include.split(",") if s.strip()} & set(_SECTIONS)


def get_person_or_404(db: Session, workspace_id: uuid.UUID, person_id: uuid.UUID) -> Person:
    row = db.execute(
        select(Person)
        .join(WorkspacePerson, WorkspacePerson.person_id == Person.id)
        .where(Person.id == person_id, WorkspacePerson.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if row is None:
        raise Stack360Error(ErrorCode.NOT_FOUND, "person não encontrada")
    return row


def get_company_or_404(db: Session, workspace_id: uuid.UUID, company_id: uuid.UUID) -> Company:
    row = db.execute(
        select(Company)
        .join(WorkspaceCompany, WorkspaceCompany.company_id == Company.id)
        .where(Company.id == company_id, WorkspaceCompany.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if row is None:
        raise Stack360Error(ErrorCode.NOT_FOUND, "company não encontrada")
    return row


def person_context(
    db: Session,
    workspace_id: uuid.UUID,
    person_id: uuid.UUID,
    *,
    limit: Optional[int] = None,
    since: Optional[datetime] = None,
    include: Optional[str] = None,
) -> dict:
    person = get_person_or_404(db, workspace_id, person_id)
    cap = limit or get_settings().context_section_limit
    want = _wanted(include)
    sk = _src_keys(db)

    out: dict = {
        "person": {
            "id": str(person.id),
            "canonical_name": person.canonical_name,
            "created_at": person.created_at,
        }
    }

    if "identities" in want:
        rows = db.execute(
            select(PersonIdentity).where(PersonIdentity.person_id == person_id)
            .order_by(PersonIdentity.last_seen_at.desc())
        ).scalars().all()
        out["identities"] = [
            {
                "identity_type": r.identity_type,
                "value_normalized": r.value_normalized,
                "is_verified": r.is_verified,
                "data_source_key": sk.get(r.data_source_id),
                "last_seen_at": r.last_seen_at,
            }
            for r in rows
        ]

    if "companies" in want:
        rows = db.execute(
            select(PersonCompanyRelationship, Company)
            .join(Company, Company.id == PersonCompanyRelationship.company_id)
            .where(
                PersonCompanyRelationship.person_id == person_id,
                PersonCompanyRelationship.workspace_id == workspace_id,
            )
            .order_by(PersonCompanyRelationship.last_seen_at.desc())
            .limit(cap)
        ).all()
        out["companies"] = [
            {
                "company": {
                    "id": str(c.id),
                    "canonical_name": c.canonical_name,
                    "domain": c.domain,
                    "cnpj_normalized": c.cnpj_normalized,
                },
                "relationship": {
                    "role": rel.role,
                    "title": rel.title,
                    "is_current": rel.is_current,
                    "first_seen_at": rel.first_seen_at,
                },
            }
            for rel, c in rows
        ]

    if "recent_interactions" in want:
        stmt = select(Interaction).where(
            Interaction.workspace_id == workspace_id, Interaction.person_id == person_id
        )
        if since:
            stmt = stmt.where(Interaction.occurred_at >= since)
        rows = db.execute(stmt.order_by(Interaction.occurred_at.desc()).limit(cap)).scalars().all()
        out["recent_interactions"] = [
            {
                "interaction_type": r.interaction_type,
                "channel": r.channel,
                "direction": r.direction,
                "occurred_at": r.occurred_at,
                "data_source_key": sk.get(r.data_source_id),
                "metadata": r.meta,
            }
            for r in rows
        ]

    if "observations" in want:
        out["observations"] = _latest_observations(
            db, workspace_id, person_col=Observation.person_id, subject_id=person_id, cap=cap, since=since, sk=sk
        )

    if "experience_runs" in want:
        stmt = (
            select(ExperienceRun, Experience)
            .join(Experience, Experience.id == ExperienceRun.experience_id)
            .where(ExperienceRun.workspace_id == workspace_id, ExperienceRun.person_id == person_id)
        )
        rows = db.execute(stmt.order_by(ExperienceRun.created_at.desc()).limit(cap)).all()
        out["experience_runs"] = [
            {
                "run_id": str(run.id),
                "experience_key": exp.key,
                "version": exp.version,
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "utm_source": run.utm_source,
                "utm_campaign": run.utm_campaign,
            }
            for run, exp in rows
        ]

    if "results" in want:
        rows = db.execute(
            select(Result)
            .join(ExperienceRun, ExperienceRun.id == Result.run_id)
            .where(Result.workspace_id == workspace_id, ExperienceRun.person_id == person_id)
            .order_by(Result.calculated_at.desc())
            .limit(cap)
        ).scalars().all()
        out["results"] = [_result_row(r) for r in rows]

    if "scores" in want:
        out["scores"] = _latest_scores(db, workspace_id, ScoreHistory.person_id, person_id, cap, sk)

    return out


def company_context(
    db: Session,
    workspace_id: uuid.UUID,
    company_id: uuid.UUID,
    *,
    limit: Optional[int] = None,
    since: Optional[datetime] = None,
    include: Optional[str] = None,
) -> dict:
    company = get_company_or_404(db, workspace_id, company_id)
    cap = limit or get_settings().context_section_limit
    want = _wanted(include)
    sk = _src_keys(db)

    out: dict = {
        "company": {
            "id": str(company.id),
            "canonical_name": company.canonical_name,
            "domain": company.domain,
            "cnpj_normalized": company.cnpj_normalized,
            "website": company.website,
            "created_at": company.created_at,
        }
    }

    if "people" in (want | {"people"}):
        rows = db.execute(
            select(PersonCompanyRelationship, Person)
            .join(Person, Person.id == PersonCompanyRelationship.person_id)
            .where(
                PersonCompanyRelationship.company_id == company_id,
                PersonCompanyRelationship.workspace_id == workspace_id,
            )
            .limit(cap)
        ).all()
        out["people"] = [
            {
                "person": {"id": str(p.id), "canonical_name": p.canonical_name},
                "relationship": {"role": rel.role, "title": rel.title, "is_current": rel.is_current},
            }
            for rel, p in rows
        ]

    if "recent_interactions" in want:
        stmt = select(Interaction).where(
            Interaction.workspace_id == workspace_id, Interaction.company_id == company_id
        )
        if since:
            stmt = stmt.where(Interaction.occurred_at >= since)
        rows = db.execute(stmt.order_by(Interaction.occurred_at.desc()).limit(cap)).scalars().all()
        out["recent_interactions"] = [
            {
                "interaction_type": r.interaction_type,
                "channel": r.channel,
                "direction": r.direction,
                "occurred_at": r.occurred_at,
                "data_source_key": sk.get(r.data_source_id),
            }
            for r in rows
        ]

    if "observations" in want:
        out["observations"] = _latest_observations(
            db, workspace_id, person_col=Observation.company_id, subject_id=company_id, cap=cap, since=since, sk=sk
        )

    if "scores" in want:
        out["scores"] = _latest_scores(db, workspace_id, ScoreHistory.company_id, company_id, cap, sk)

    return out


def _latest_observations(db, workspace_id, *, person_col, subject_id, cap, since, sk):
    stmt = select(Observation).where(
        Observation.workspace_id == workspace_id, person_col == subject_id
    )
    if since:
        stmt = stmt.where(Observation.observed_at >= since)
    rows = db.execute(stmt.order_by(Observation.observed_at.desc())).scalars().all()
    seen: set[str] = set()
    latest = []
    for r in rows:
        if r.key in seen:
            continue
        seen.add(r.key)
        latest.append(
            {
                "key": r.key,
                "value": r.value,
                "confidence": float(r.confidence) if r.confidence is not None else None,
                "source_kind": r.source_kind,
                "data_source_key": sk.get(r.data_source_id),
                "observed_at": r.observed_at,
            }
        )
        if len(latest) >= cap:
            break
    return latest


def _latest_scores(db, workspace_id, subject_col, subject_id, cap, sk):
    rows = db.execute(
        select(ScoreHistory)
        .where(ScoreHistory.workspace_id == workspace_id, subject_col == subject_id)
        .order_by(ScoreHistory.calculated_at.desc())
    ).scalars().all()
    seen: set[str] = set()
    latest = []
    for r in rows:
        if r.score_key in seen:
            continue
        seen.add(r.score_key)
        latest.append(
            {
                "score_key": r.score_key,
                "score_value": float(r.score_value),
                "score_band": r.score_band,
                "calculated_at": r.calculated_at,
                "data_source_key": sk.get(r.data_source_id),
            }
        )
        if len(latest) >= cap:
            break
    return latest


def _result_row(r: Result) -> dict:
    return {
        "run_id": str(r.run_id),
        "result_type": r.result_type,
        "score": float(r.score) if r.score is not None else None,
        "verdict": r.verdict,
        "score_band": r.score_band,
        "engine_name": r.engine_name,
        "engine_version": r.engine_version,
        "calculated_at": r.calculated_at,
    }

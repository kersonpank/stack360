"""Lógica das tools MCP — REUSA os mesmos services da REST (zero divergência).

Cada função recebe (auth, Session_) e devolve dict serializável.
NENHUMA tool arbitra workspace_id — vem sempre da AuthContext (key).
``submit_resolution_recommendation`` só cria recommendation: NUNCA faz merge
nem altera Person/Company/identidade.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select

from app.stack360.auth import AuthContext, require_scope, resolve_source
from app.stack360.ingestion.gateway import ingest_one
from app.stack360.models.company import Company, WorkspaceCompany
from app.stack360.models.data_source import DataSource
from app.stack360.models.experience import Experience, ExperienceRun
from app.stack360.models.interaction import Interaction
from app.stack360.models.person import Person, PersonIdentity, WorkspacePerson
from app.stack360.models.resolution import ResolutionCase, ResolutionRecommendation
from app.stack360.resolution.normalize import normalize_identity
from app.stack360.schemas.envelope import StackEvent
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.services import context as ctxsvc
from app.stack360.base import utcnow


# ---------- READ ----------
def search_people(auth: AuthContext, S, query: Optional[str] = None, identity_type: Optional[str] = None, identity_value: Optional[str] = None, limit: int = 25):
    require_scope(auth, "read") if "read" in auth.scopes else require_scope(auth, "mcp")
    with S() as db:
        stmt = select(Person).join(WorkspacePerson, WorkspacePerson.person_id == Person.id).where(
            WorkspacePerson.workspace_id == auth.workspace_id
        )
        if query:
            stmt = stmt.where(Person.canonical_name.ilike(f"%{query}%"))
        if identity_type and identity_value:
            ni = normalize_identity(identity_type, identity_value, has_data_source=True)
            if ni:
                stmt = stmt.join(PersonIdentity, PersonIdentity.person_id == Person.id).where(
                    PersonIdentity.identity_type == ni.identity_type,
                    PersonIdentity.value_hash == ni.value_hash,
                )
        rows = db.execute(stmt.order_by(Person.created_at.desc()).limit(limit)).scalars().all()
        return {"items": [{"id": str(p.id), "canonical_name": p.canonical_name} for p in rows]}


def get_person(auth: AuthContext, S, person_id: str):
    with S() as db:
        p = ctxsvc.get_person_or_404(db, auth.workspace_id, uuid.UUID(person_id))
        return {"id": str(p.id), "canonical_name": p.canonical_name, "created_at": p.created_at.isoformat()}


def get_person_context(auth: AuthContext, S, person_id: str, limit: Optional[int] = None, include: Optional[str] = None):
    with S() as db:
        return _jsonable(ctxsvc.person_context(db, auth.workspace_id, uuid.UUID(person_id), limit=limit, include=include))


def search_companies(auth: AuthContext, S, query: Optional[str] = None, domain: Optional[str] = None, limit: int = 25):
    with S() as db:
        stmt = select(Company).join(WorkspaceCompany, WorkspaceCompany.company_id == Company.id).where(
            WorkspaceCompany.workspace_id == auth.workspace_id
        )
        if query:
            stmt = stmt.where(Company.canonical_name.ilike(f"%{query}%"))
        if domain:
            stmt = stmt.where(Company.domain == domain.lower())
        rows = db.execute(stmt.limit(limit)).scalars().all()
        return {"items": [{"id": str(c.id), "canonical_name": c.canonical_name, "domain": c.domain} for c in rows]}


def get_company(auth: AuthContext, S, company_id: str):
    with S() as db:
        c = ctxsvc.get_company_or_404(db, auth.workspace_id, uuid.UUID(company_id))
        return {"id": str(c.id), "canonical_name": c.canonical_name, "domain": c.domain, "cnpj_normalized": c.cnpj_normalized}


def get_company_context(auth: AuthContext, S, company_id: str, limit: Optional[int] = None, include: Optional[str] = None):
    with S() as db:
        return _jsonable(ctxsvc.company_context(db, auth.workspace_id, uuid.UUID(company_id), limit=limit, include=include))


def list_recent_interactions(auth: AuthContext, S, person_id: Optional[str] = None, company_id: Optional[str] = None, limit: int = 25):
    with S() as db:
        stmt = select(Interaction).where(Interaction.workspace_id == auth.workspace_id)
        if person_id:
            stmt = stmt.where(Interaction.person_id == uuid.UUID(person_id))
        if company_id:
            stmt = stmt.where(Interaction.company_id == uuid.UUID(company_id))
        rows = db.execute(stmt.order_by(Interaction.occurred_at.desc()).limit(limit)).scalars().all()
        return {
            "items": [
                {
                    "id": str(r.id),
                    "interaction_type": r.interaction_type,
                    "channel": r.channel,
                    "direction": r.direction,
                    "occurred_at": r.occurred_at.isoformat(),
                }
                for r in rows
            ]
        }


def list_experience_runs(auth: AuthContext, S, experience_key: Optional[str] = None, limit: int = 25):
    with S() as db:
        stmt = select(ExperienceRun).where(ExperienceRun.workspace_id == auth.workspace_id)
        if experience_key:
            stmt = stmt.join(Experience, Experience.id == ExperienceRun.experience_id).where(
                Experience.key == experience_key
            )
        rows = db.execute(stmt.order_by(ExperienceRun.created_at.desc()).limit(limit)).scalars().all()
        return {
            "items": [
                {"id": str(r.id), "status": r.status, "external_run_id": r.external_run_id,
                 "person_id": str(r.person_id) if r.person_id else None}
                for r in rows
            ]
        }


def get_experience_run(auth: AuthContext, S, run_id: str):
    with S() as db:
        r = db.get(ExperienceRun, uuid.UUID(run_id))
        if r is None or r.workspace_id != auth.workspace_id:
            raise Stack360Error(ErrorCode.NOT_FOUND, "run não encontrada")
        return {
            "id": str(r.id),
            "status": r.status,
            "person_id": str(r.person_id) if r.person_id else None,
            "company_id": str(r.company_id) if r.company_id else None,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }


def list_sources(auth: AuthContext, S):
    with S() as db:
        rows = db.execute(
            select(DataSource).where(DataSource.workspace_id == auth.workspace_id)
        ).scalars().all()
        return {"items": [{"key": s.key, "name": s.name, "status": s.status} for s in rows]}


def get_source_health(auth: AuthContext, S):
    from app.stack360.api.sources import sources_health  # reusa a mesma lógica

    class _Ctx:
        workspace_id = auth.workspace_id

    with S() as db:
        return _jsonable(sources_health(_Ctx(), db))


def list_resolution_cases(auth: AuthContext, S, status: Optional[str] = None, case_type: Optional[str] = None, limit: int = 50):
    with S() as db:
        stmt = select(ResolutionCase).where(ResolutionCase.workspace_id == auth.workspace_id)
        if status:
            stmt = stmt.where(ResolutionCase.status == status)
        if case_type:
            stmt = stmt.where(ResolutionCase.case_type == case_type)
        rows = db.execute(stmt.order_by(ResolutionCase.created_at.desc()).limit(limit)).scalars().all()
        return {
            "items": [
                {"id": str(c.id), "case_type": c.case_type, "status": c.status, "severity": c.severity}
                for c in rows
            ]
        }


def get_resolution_case(auth: AuthContext, S, case_id: str):
    with S() as db:
        c = db.get(ResolutionCase, uuid.UUID(case_id))
        if c is None or c.workspace_id != auth.workspace_id:
            raise Stack360Error(ErrorCode.NOT_FOUND, "caso não encontrado")
        recs = db.execute(
            select(ResolutionRecommendation).where(ResolutionRecommendation.resolution_case_id == c.id)
        ).scalars().all()
        return {
            "id": str(c.id),
            "case_type": c.case_type,
            "status": c.status,
            "severity": c.severity,
            "details": c.details,
            "recommendations": [
                {"recommended_action": r.recommended_action, "confidence": float(r.confidence) if r.confidence is not None else None, "summary": r.summary}
                for r in recs
            ],
        }


# ---------- WRITE (scope ingest) ----------
def ingest_event(auth: AuthContext, S, envelope: dict[str, Any]):
    require_scope(auth, "ingest")
    if auth.data_source_id is None:
        raise Stack360Error(ErrorCode.SCOPE_DENIED, "ingest via MCP exige key source-bound")
    with S() as _db:
        resolve_source(_db, auth)  # 403 SOURCE_DISABLED se a data_source não estiver ativa
    event = StackEvent.model_validate(envelope)
    res = ingest_one(S, auth, event, event.model_dump(mode="json"))
    body = {"status": res.status, "event_id": res.external_event_id, "entities": res.entities}
    if res.resolution_case_id:
        body["resolution_case_id"] = str(res.resolution_case_id)
    return body


def record_observation(auth: AuthContext, S, key: str, value: Any, subject_identities: list[dict], event_id: str, occurred_at: Optional[str] = None, confidence: Optional[float] = None):
    envelope = {
        "schema_version": "1.0",
        "event_id": event_id,
        "event_type": "observation.recorded",
        "occurred_at": occurred_at or utcnow().isoformat(),
        "subject": {"identities": subject_identities},
        "data": {"key": key, "value": value, "confidence": confidence, "source_kind": "declared"},
    }
    return ingest_event(auth, S, envelope)


def record_interaction(auth: AuthContext, S, interaction_type: str, subject_identities: list[dict], event_id: str, channel: Optional[str] = None, direction: Optional[str] = None, occurred_at: Optional[str] = None):
    envelope = {
        "schema_version": "1.0",
        "event_id": event_id,
        "event_type": f"interaction.{interaction_type}",
        "occurred_at": occurred_at or utcnow().isoformat(),
        "subject": {"identities": subject_identities},
        "context": {"channel": channel, "direction": direction},
        "data": {},
    }
    return ingest_event(auth, S, envelope)


def submit_resolution_recommendation(
    auth: AuthContext,
    S,
    resolution_case_id: str,
    recommended_action: str,
    evidence: dict,
    confidence: Optional[float] = None,
    summary: Optional[str] = None,
    candidate_entity_ids: Optional[list] = None,
    agent_name: Optional[str] = None,
    agent_version: Optional[str] = None,
):
    """SÓ cria recommendation. NUNCA faz merge nem altera identidade."""
    require_scope(auth, "mcp") if "mcp" in auth.scopes else require_scope(auth, "read")
    with S() as db:
        case = db.get(ResolutionCase, uuid.UUID(resolution_case_id))
        if case is None or case.workspace_id != auth.workspace_id:
            raise Stack360Error(ErrorCode.NOT_FOUND, "resolution_case não encontrado")
        rec = ResolutionRecommendation(
            resolution_case_id=case.id,
            recommended_action=recommended_action,
            candidate_entity_ids=candidate_entity_ids or [],
            confidence=confidence,
            evidence=evidence or {},
            summary=summary,
            agent_name=agent_name,
            agent_version=agent_version,
        )
        db.add(rec)
        if case.status == "open":
            case.status = "recommendation_ready"
        db.commit()
        return {"recommendation_id": str(rec.id), "case_status": case.status}


def _jsonable(obj):
    import json

    return json.loads(json.dumps(obj, default=str))

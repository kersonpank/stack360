from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select

from app.stack360.base import utcnow
from app.stack360.ingestion.handlers import HandlerContext
from app.stack360.models.company import PersonCompanyRelationship
from app.stack360.resolution.company import resolve_company
from app.stack360.resolution.identity import PersonResolution, resolve_person
from app.stack360.schemas.envelope import IdentityIn


def resolve_person_from_event(ctx: HandlerContext, *, name_hint: Optional[str] = None) -> PersonResolution:
    idents: list[IdentityIn] = list(ctx.event.subject.identities) if ctx.event.subject else []
    res = resolve_person(
        ctx.db,
        workspace_id=ctx.workspace_id,
        data_source_id=ctx.data_source_id,
        identities_in=idents,
        name_hint=name_hint or (ctx.event.data.get("name") if isinstance(ctx.event.data, dict) else None),
    )
    if res.person_id:
        ctx.entities["person_id"] = str(res.person_id)
    return res


def resolve_company_from_event(ctx: HandlerContext) -> Optional[uuid.UUID]:
    cres = resolve_company(ctx.db, workspace_id=ctx.workspace_id, company_in=ctx.event.company)
    if cres is None:
        return None
    if cres.ambiguous:
        ctx.pending_cases.append(
            {
                "case_type": "possible_duplicate_company"
                if cres.ambiguous_on == "domain"
                else "company_conflict",
                "severity": "medium",
                "subject_type": "company",
                "subject_id": None,
                "details": {
                    "ambiguous_on": cres.ambiguous_on,
                    "candidate_company_ids": [str(i) for i in cres.candidate_ids],
                    "company_input": ctx.event.company.model_dump(exclude_none=True)
                    if ctx.event.company
                    else {},
                },
            }
        )
        return None
    if cres.company_id:
        ctx.entities["company_id"] = str(cres.company_id)
    return cres.company_id


def link_person_company(ctx: HandlerContext, person_id: Optional[uuid.UUID], company_id: Optional[uuid.UUID]) -> None:
    """Cria/atualiza person_company_relationships quando ambos resolvem no evento.
    Histórico preservado: só uma linha por (person, company, role); nunca update destrutivo de outra role."""
    if not person_id or not company_id:
        return
    data = ctx.event.data if isinstance(ctx.event.data, dict) else {}
    role = data.get("role")
    existing = ctx.db.execute(
        select(PersonCompanyRelationship).where(
            PersonCompanyRelationship.workspace_id == ctx.workspace_id,
            PersonCompanyRelationship.person_id == person_id,
            PersonCompanyRelationship.company_id == company_id,
            PersonCompanyRelationship.role.is_(role) if role is None else PersonCompanyRelationship.role == role,
        )
    ).scalar_one_or_none()
    now = utcnow()
    if existing is not None:
        existing.last_seen_at = now
        return
    ctx.db.add(
        PersonCompanyRelationship(
            workspace_id=ctx.workspace_id,
            person_id=person_id,
            company_id=company_id,
            role=role,
            title=data.get("title"),
            department=data.get("department"),
            is_current=data.get("is_current"),
            data_source_id=ctx.data_source_id,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    ctx.db.flush()

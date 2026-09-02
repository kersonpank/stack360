"""Resolução de empresa — conservadora. CNPJ > domínio (só se 1 candidata) >
nome inequívoco. Sem fuzzy, sem merge. ``domain`` NÃO é unique — 2 companies
podem compartilhar. Ambiguidade => cria resolution_case (via gateway).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.stack360.base import utcnow
from app.stack360.models.company import Company, WorkspaceCompany
from app.stack360.resolution.normalize import (
    normalize_cnpj,
    normalize_company_name,
    normalize_domain,
)
from app.stack360.schemas.envelope import CompanyIn


@dataclass
class CompanyResolution:
    company_id: Optional[uuid.UUID]
    created: bool = False
    ambiguous: bool = False
    ambiguous_on: Optional[str] = None  # "domain" | "name"
    candidate_ids: list[uuid.UUID] = None  # type: ignore

    def __post_init__(self):
        if self.candidate_ids is None:
            self.candidate_ids = []


def resolve_company(
    db: Session, *, workspace_id: uuid.UUID, company_in: Optional[CompanyIn]
) -> Optional[CompanyResolution]:
    if company_in is None or company_in.is_empty():
        return None

    cnpj = normalize_cnpj(company_in.cnpj or "")
    domain = normalize_domain(company_in.domain or "")
    norm_name = normalize_company_name(company_in.name or "")

    # 1. CNPJ exato
    if cnpj:
        row = db.execute(select(Company).where(Company.cnpj_normalized == cnpj)).scalar_one_or_none()
        if row is not None:
            _upsert_workspace_company(db, workspace_id, row.id)
            return CompanyResolution(company_id=row.id)

    # 2. domínio exato — só resolve se EXATAMENTE 1 candidata SEGURA.
    #    Se o evento traz um CNPJ que NÃO bate com o da candidata (empresas
    #    distintas que compartilham domínio, ex. subsidiárias), NÃO resolve.
    if domain:
        cands = db.execute(select(Company).where(Company.domain == domain)).scalars().all()
        safe = [
            c for c in cands
            if not (cnpj and c.cnpj_normalized and c.cnpj_normalized != cnpj)
        ]
        if len(safe) == 1:
            _maybe_backfill(db, safe[0].id, cnpj)
            _upsert_workspace_company(db, workspace_id, safe[0].id)
            return CompanyResolution(company_id=safe[0].id)
        if len(safe) > 1:
            return CompanyResolution(
                company_id=None, ambiguous=True, ambiguous_on="domain",
                candidate_ids=[c.id for c in safe],
            )

    # 3. nome inequívoco — só resolve se EXATAMENTE 1 candidata
    if norm_name:
        ids = (
            db.execute(select(Company.id).where(Company.normalized_name == norm_name)).scalars().all()
        )
        if len(ids) == 1:
            _maybe_backfill(db, ids[0], cnpj, domain)
            _upsert_workspace_company(db, workspace_id, ids[0])
            return CompanyResolution(company_id=ids[0])
        if len(ids) > 1:
            return CompanyResolution(
                company_id=None, ambiguous=True, ambiguous_on="name", candidate_ids=list(ids)
            )

    # 4. cria
    company = Company(
        canonical_name=(company_in.name or None),
        normalized_name=norm_name,
        domain=domain,
        cnpj_normalized=cnpj,
        website=(company_in.domain or None),
    )
    db.add(company)
    db.flush()
    _upsert_workspace_company(db, workspace_id, company.id)
    return CompanyResolution(company_id=company.id, created=True)


def _maybe_backfill(db: Session, company_id: uuid.UUID, cnpj: Optional[str] = None, domain: Optional[str] = None) -> None:
    c = db.get(Company, company_id)
    if c is None:
        return
    if cnpj and not c.cnpj_normalized:
        c.cnpj_normalized = cnpj
    if domain and not c.domain:
        c.domain = domain


def _upsert_workspace_company(db: Session, workspace_id: uuid.UUID, company_id: uuid.UUID) -> None:
    wc = db.get(WorkspaceCompany, {"workspace_id": workspace_id, "company_id": company_id})
    now = utcnow()
    if wc is None:
        db.add(
            WorkspaceCompany(
                workspace_id=workspace_id, company_id=company_id, first_seen_at=now, last_seen_at=now
            )
        )
    else:
        wc.last_seen_at = now

"""Resolução de identidade — determinística, sem fuzzy, sem merge.

- Fortes globais (v1): SOMENTE ``email`` / ``phone`` (match global).
- Demais: match por ``(data_source_id, identity_type, value_hash)``.
- >=2 Persons distintas a partir de identidade FORTE => IdentityConflict
  (o gateway preserva o raw, marca 'conflict' e cria 1 resolution_case).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.stack360.base import utcnow
from app.stack360.models.person import Person, PersonIdentity, WorkspacePerson
from app.stack360.resolution.normalize import NormalizedIdentity, normalize_identity
from app.stack360.schemas.envelope import IdentityIn


class IdentityConflict(Exception):
    def __init__(self, person_ids: list[uuid.UUID], identities: list[NormalizedIdentity]):
        super().__init__("multiple persons match strong identities")
        self.person_ids = person_ids
        self.identities = identities


@dataclass
class PersonResolution:
    person_id: Optional[uuid.UUID]
    normalized: list[NormalizedIdentity] = field(default_factory=list)
    invalid: list[dict] = field(default_factory=list)
    created: bool = False


def _lookup_person_id(
    db: Session, ni: NormalizedIdentity, data_source_id: Optional[uuid.UUID]
) -> Optional[uuid.UUID]:
    stmt = select(PersonIdentity.person_id).where(
        PersonIdentity.identity_type == ni.identity_type,
        PersonIdentity.value_hash == ni.value_hash,
    )
    if ni.source_scoped:
        stmt = stmt.where(PersonIdentity.data_source_id == data_source_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none()


def resolve_person(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    data_source_id: Optional[uuid.UUID],
    identities_in: list[IdentityIn],
    name_hint: Optional[str] = None,
) -> PersonResolution:
    normalized: list[NormalizedIdentity] = []
    invalid: list[dict] = []
    for ident in identities_in:
        ni = normalize_identity(ident.type, ident.value, has_data_source=data_source_id is not None)
        if ni is None:
            invalid.append({"type": ident.type, "value_present": bool(ident.value)})
        else:
            normalized.append(ni)

    if not normalized:
        return PersonResolution(person_id=None, normalized=[], invalid=invalid)

    strong_person_ids: set[uuid.UUID] = set()
    any_person_ids: set[uuid.UUID] = set()
    for ni in normalized:
        pid = _lookup_person_id(db, ni, data_source_id)
        if pid is not None:
            any_person_ids.add(pid)
            if ni.is_strong_global:
                strong_person_ids.add(pid)

    if len(strong_person_ids) >= 2:
        raise IdentityConflict(sorted(strong_person_ids, key=str), normalized)

    person_id = next(iter(strong_person_ids), None) or next(iter(any_person_ids), None)
    created = False

    if person_id is None:
        person = Person(canonical_name=name_hint)
        db.add(person)
        db.flush()
        person_id = person.id
        created = True
    elif name_hint:
        person = db.get(Person, person_id)
        if person is not None and not person.canonical_name:
            person.canonical_name = name_hint

    # Anexa identidades ainda não presentes
    for ni in normalized:
        row = db.execute(
            select(PersonIdentity).where(
                PersonIdentity.person_id == person_id,
                PersonIdentity.identity_type == ni.identity_type,
                PersonIdentity.value_hash == ni.value_hash,
                *([PersonIdentity.data_source_id == data_source_id] if ni.source_scoped else []),
            )
        ).scalar_one_or_none()
        if row is not None:
            row.last_seen_at = utcnow()
            continue
        db.add(
            PersonIdentity(
                person_id=person_id,
                data_source_id=data_source_id if ni.source_scoped else None,
                identity_type=ni.identity_type,
                value_normalized=ni.value_normalized,
                value_hash=ni.value_hash,
                is_verified=False,
            )
        )

    _upsert_workspace_person(db, workspace_id, person_id)
    db.flush()
    return PersonResolution(person_id=person_id, normalized=normalized, invalid=invalid, created=created)


def _upsert_workspace_person(db: Session, workspace_id: uuid.UUID, person_id: uuid.UUID) -> None:
    wp = db.get(WorkspacePerson, {"workspace_id": workspace_id, "person_id": person_id})
    now = utcnow()
    if wp is None:
        db.add(
            WorkspacePerson(
                workspace_id=workspace_id, person_id=person_id, first_seen_at=now, last_seen_at=now
            )
        )
    else:
        wp.last_seen_at = now


def link_identities_to_person(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    data_source_id: Optional[uuid.UUID],
    person_id: uuid.UUID,
    identities_in: list[IdentityIn],
) -> list[NormalizedIdentity]:
    """Usado por experience.identity_captured quando já há um person_id de destino."""
    out: list[NormalizedIdentity] = []
    for ident in identities_in:
        ni = normalize_identity(ident.type, ident.value, has_data_source=data_source_id is not None)
        if ni is None:
            continue
        out.append(ni)
        existing = _lookup_person_id(db, ni, data_source_id)
        if existing == person_id:
            continue
        db.add(
            PersonIdentity(
                person_id=person_id,
                data_source_id=data_source_id if ni.source_scoped else None,
                identity_type=ni.identity_type,
                value_normalized=ni.value_normalized,
                value_hash=ni.value_hash,
                is_verified=ident.verified,
            )
        )
    _upsert_workspace_person(db, workspace_id, person_id)
    db.flush()
    return out

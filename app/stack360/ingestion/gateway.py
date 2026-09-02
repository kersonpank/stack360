"""Ingestion Gateway — 3 transações. O raw ingestion_event SEMPRE sobrevive.

TX A  persiste o raw (durável)                -> COMMIT
TX B  claim (FOR UPDATE SKIP LOCKED) + handler + writes canônicos -> COMMIT | ROLLBACK
TX C  registra failed/conflict + resolution_case                  -> COMMIT
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from app.stack360.auth import AuthContext
from app.stack360.base import utcnow
from app.stack360.ingestion.handlers import HandlerContext, get_handler, load_handlers
from app.stack360.models.data_source import SourceSyncState
from app.stack360.models.ingestion_event import (
    CONFLICT,
    FAILED,
    PENDING,
    PROCESSED,
    IngestionEvent,
)
from app.stack360.models.resolution import ResolutionCase
from app.stack360.observability import log_event
from app.stack360.resolution.identity import IdentityConflict
from app.stack360.schemas.envelope import StackEvent, schema_major_supported
from app.stack360.schemas.errors import ErrorCode, Stack360Error
from app.stack360.security.hashing import payload_hash

load_handlers()


@dataclass
class IngestResult:
    status: str  # accepted | duplicate | processing | conflict | error
    external_event_id: str
    ingestion_event_id: Optional[uuid.UUID] = None
    entities: dict[str, Any] = field(default_factory=dict)
    error: Optional[Stack360Error] = None
    resolution_case_id: Optional[uuid.UUID] = None

    @property
    def ok(self) -> bool:
        return self.status in ("accepted", "duplicate", "processing")


def _schema_major(sv: str) -> str:
    return str(sv).split(".", 1)[0]


def _persist_raw(
    db: Session, auth: AuthContext, event: StackEvent, raw_payload: dict
) -> tuple[uuid.UUID, str, Optional[dict]]:
    """TX A: retorna (ingestion_event_id, initial_status, existing_meta).

    ``existing_meta`` é None quando a linha é nova; caso contrário
    ``{"payload_hash", "event_type", "schema_version"}`` do evento já persistido
    (H2 — detecção de reutilização de event_id com payload/contrato diferente).
    """
    stmt = (
        pg_insert(IngestionEvent)
        .values(
            workspace_id=auth.workspace_id,
            data_source_id=auth.data_source_id,
            external_event_id=event.event_id,
            schema_version=event.schema_version,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            received_at=utcnow(),
            payload=raw_payload,
            payload_hash=payload_hash(raw_payload),
            status=PENDING,
        )
        .on_conflict_do_nothing(index_elements=["data_source_id", "external_event_id"])
        .returning(IngestionEvent.id)
    )
    new_id = db.execute(stmt).scalar_one_or_none()
    db.commit()
    if new_id is not None:
        return new_id, PENDING, None

    row = db.execute(
        select(
            IngestionEvent.id,
            IngestionEvent.status,
            IngestionEvent.payload_hash,
            IngestionEvent.event_type,
            IngestionEvent.schema_version,
        ).where(
            IngestionEvent.data_source_id == auth.data_source_id,
            IngestionEvent.external_event_id == event.event_id,
        )
    ).one()
    return row.id, row.status, {
        "payload_hash": row.payload_hash,
        "event_type": row.event_type,
        "schema_version": row.schema_version,
    }


def _event_id_conflict_case(
    Session_: sessionmaker, *, ie_id: uuid.UUID, workspace_id: uuid.UUID, details: dict
) -> Optional[uuid.UUID]:
    """H2: cria (idempotentemente) o resolution_case do conflito de event_id.
    NÃO toca no ingestion_event original (payload/status/retry_count intactos)."""
    from sqlalchemy.exc import IntegrityError

    with Session_() as db:
        try:
            case_id = _create_case(
                db,
                workspace_id=workspace_id,
                ie_id=ie_id,
                case_type="event_id_conflict",
                severity="high",
                details=details,
            )
            db.commit()
            return case_id
        except IntegrityError:
            db.rollback()
            return _open_case_id(db, workspace_id, ie_id, "event_id_conflict")


def _touch_sync(db: Session, data_source_id: uuid.UUID, *, ok: bool, err_msg: Optional[str] = None) -> None:
    st = db.get(SourceSyncState, data_source_id)
    now = utcnow()
    if st is None:
        st = SourceSyncState(data_source_id=data_source_id)
        db.add(st)
    st.last_seen_at = now
    st.updated_at = now
    if ok:
        st.last_success_at = now
    else:
        st.last_error_at = now
        st.last_error_message = (err_msg or "")[:1000]


def _open_case_id(db: Session, workspace_id: uuid.UUID, ie_id: uuid.UUID, case_type: str) -> Optional[uuid.UUID]:
    return db.execute(
        select(ResolutionCase.id).where(
            ResolutionCase.workspace_id == workspace_id,
            ResolutionCase.ingestion_event_id == ie_id,
            ResolutionCase.case_type == case_type,
            ResolutionCase.status.notin_(("resolved", "dismissed")),
        )
    ).scalar_one_or_none()


def _create_case(
    db: Session,
    *,
    workspace_id: uuid.UUID,
    ie_id: uuid.UUID,
    case_type: str,
    severity: str,
    details: dict,
    subject_type: Optional[str] = None,
    subject_id: Optional[uuid.UUID] = None,
) -> uuid.UUID:
    existing = _open_case_id(db, workspace_id, ie_id, case_type)
    if existing is not None:
        return existing
    case = ResolutionCase(
        workspace_id=workspace_id,
        ingestion_event_id=ie_id,
        case_type=case_type,
        status="open",
        severity=severity,
        subject_type=subject_type,
        subject_id=subject_id,
        details=details,
    )
    db.add(case)
    db.flush()
    return case.id


def _tx_c_fail(
    Session_: sessionmaker,
    *,
    ie_id: uuid.UUID,
    workspace_id: uuid.UUID,
    status: str,
    err: Stack360Error,
    case: Optional[dict] = None,
) -> Optional[uuid.UUID]:
    with Session_() as db:
        ie = db.get(IngestionEvent, ie_id)
        ie.status = status
        ie.error_code = err.code.value
        ie.error_message = err.message[:1000]
        ie.retry_count = (ie.retry_count or 0) + 1
        ie.processed_at = None
        case_id = None
        if case is not None:
            case_id = _create_case(
                db,
                workspace_id=workspace_id,
                ie_id=ie_id,
                case_type=case["case_type"],
                severity=case.get("severity", "high"),
                details=case.get("details", {}),
                subject_type=case.get("subject_type"),
            )
        _touch_sync(db, ie.data_source_id, ok=False, err_msg=err.message)
        db.commit()
        return case_id


def ingest_one(Session_: sessionmaker, auth: AuthContext, event: StackEvent, raw_payload: dict) -> IngestResult:
    if not schema_major_supported(event.schema_version):
        return IngestResult(
            status="error",
            external_event_id=event.event_id,
            error=Stack360Error(
                ErrorCode.SCHEMA_UNSUPPORTED, f"schema_version não suportado: {event.schema_version!r}"
            ),
        )

    # ── TX A ────────────────────────────────────────────────
    with Session_() as db:
        ie_id, status0, existing_meta = _persist_raw(db, auth, event, raw_payload)

    # H2 — reutilização de (data_source, external_event_id) com contrato incompatível
    if existing_meta is not None:
        incoming_hash = payload_hash(raw_payload)
        compatible = (
            existing_meta["payload_hash"] == incoming_hash
            and existing_meta["event_type"] == event.event_type
            and _schema_major(existing_meta["schema_version"]) == _schema_major(event.schema_version)
        )
        if not compatible:
            details = {
                "event_id": event.event_id,
                "source": auth.data_source_key,
                "event_type": event.event_type,
                "existing_event_type": existing_meta["event_type"],
                "existing_payload_hash": existing_meta["payload_hash"],
                "incoming_payload_hash": incoming_hash,
            }
            err = Stack360Error(
                ErrorCode.EVENT_ID_CONFLICT,
                "external_event_id reutilizado com payload/contrato incompatível; "
                "o ingestion_event original permanece intacto",
                details,
            )
            rc_id = _event_id_conflict_case(
                Session_, ie_id=ie_id, workspace_id=auth.workspace_id, details=details
            )
            log_event(event, ie_id, "event_id_conflict", auth, error_code=err.code.value)
            return IngestResult("conflict", event.event_id, ie_id, error=err, resolution_case_id=rc_id)

    if status0 == PROCESSED:
        return IngestResult("duplicate", event.event_id, ie_id)
    if status0 == CONFLICT:
        with Session_() as db:
            rc_id = _open_case_id(db, auth.workspace_id, ie_id, "identity_conflict")
        return IngestResult(
            "conflict",
            event.event_id,
            ie_id,
            error=Stack360Error(ErrorCode.IDENTITY_CONFLICT, "evento já em conflito de identidade"),
            resolution_case_id=rc_id,
        )

    # ── TX B ────────────────────────────────────────────────
    with Session_() as db:
        claimed = db.execute(
            text(
                "SELECT id FROM stack360.ingestion_events "
                "WHERE id = :id AND status IN ('pending','failed') "
                "FOR UPDATE SKIP LOCKED"
            ),
            {"id": str(ie_id)},
        ).scalar_one_or_none()

        if claimed is None:
            cur = db.execute(
                select(IngestionEvent.status).where(IngestionEvent.id == ie_id)
            ).scalar_one()
            db.rollback()
            if cur == PROCESSED:
                return IngestResult("duplicate", event.event_id, ie_id)
            if cur == CONFLICT:
                rc_id = _open_case_id(db, auth.workspace_id, ie_id, "identity_conflict")
                return IngestResult(
                    "conflict", event.event_id, ie_id,
                    error=Stack360Error(ErrorCode.IDENTITY_CONFLICT, "evento em conflito"),
                    resolution_case_id=rc_id,
                )
            # outro worker/request está processando este MESMO evento
            return IngestResult("processing", event.event_id, ie_id)

        ie = db.get(IngestionEvent, ie_id)
        hctx = HandlerContext(db=db, auth=auth, event=event, ingestion_event=ie)
        handler = get_handler(event.event_type)
        if handler is None:
            db.rollback()
            err = Stack360Error(
                ErrorCode.VALIDATION_ERROR,
                f"nenhum handler para event_type '{event.event_type}'",
            )
            _tx_c_fail(Session_, ie_id=ie_id, workspace_id=auth.workspace_id, status=FAILED, err=err)
            log_event(event, ie_id, "failed", auth, error_code=err.code.value)
            return IngestResult("error", event.event_id, ie_id, error=err)

        try:
            handler(hctx)
            for c in hctx.pending_cases:
                _create_case(
                    db,
                    workspace_id=auth.workspace_id,
                    ie_id=ie_id,
                    case_type=c["case_type"],
                    severity=c.get("severity", "medium"),
                    details=c.get("details", {}),
                    subject_type=c.get("subject_type"),
                )
            ie.status = PROCESSED
            ie.processed_at = utcnow()
            ie.error_code = None
            ie.error_message = None
            _touch_sync(db, auth.data_source_id, ok=True)
            db.commit()
            log_event(event, ie_id, "processed", auth, entities=hctx.entities)
            return IngestResult("accepted", event.event_id, ie_id, entities=hctx.entities)

        except IdentityConflict as conflict:
            db.rollback()
            case = {
                "case_type": "identity_conflict",
                "severity": "high",
                "subject_type": "person",
                "details": {
                    "candidate_person_ids": [str(p) for p in conflict.person_ids],
                    "identities": [
                        {"type": ni.identity_type, "value_hash": ni.value_hash}
                        for ni in conflict.identities
                    ],
                },
            }
            err = Stack360Error(
                ErrorCode.IDENTITY_CONFLICT,
                "identidades fortes do evento apontam para Persons diferentes",
                {"candidate_person_ids": [str(p) for p in conflict.person_ids]},
            )
            rc_id = _tx_c_fail(
                Session_, ie_id=ie_id, workspace_id=auth.workspace_id, status=CONFLICT, err=err, case=case
            )
            log_event(event, ie_id, "conflict", auth, error_code=err.code.value)
            return IngestResult("conflict", event.event_id, ie_id, error=err, resolution_case_id=rc_id)

        except Stack360Error as err:
            db.rollback()
            case = None
            if err.code == ErrorCode.EXPERIENCE_NOT_FOUND:
                case = {
                    "case_type": "ingestion_error",
                    "severity": "medium",
                    "details": {"error_code": err.code.value, "message": err.message, **err.details},
                }
            _tx_c_fail(
                Session_, ie_id=ie_id, workspace_id=auth.workspace_id, status=FAILED, err=err, case=case
            )
            log_event(event, ie_id, "failed", auth, error_code=err.code.value)
            return IngestResult("error", event.event_id, ie_id, error=err)

        except Exception as exc:  # noqa: BLE001
            db.rollback()
            err = Stack360Error(ErrorCode.INTERNAL_ERROR, "erro interno ao processar evento")
            _tx_c_fail(Session_, ie_id=ie_id, workspace_id=auth.workspace_id, status=FAILED, err=err)
            log_event(event, ie_id, "failed", auth, error_code="INTERNAL_ERROR", extra={"exc": type(exc).__name__})
            return IngestResult("error", event.event_id, ie_id, error=err)


def reprocess(Session_: sessionmaker, ie_id: uuid.UUID) -> IngestResult:
    """Re-roda TX B sobre um ingestion_event 'failed'/'conflict'. Usado pelo admin CLI."""
    from app.stack360.auth import AuthContext as _AC
    from app.stack360.models.data_source import DataSource

    with Session_() as db:
        ie = db.get(IngestionEvent, ie_id)
        if ie is None:
            raise Stack360Error(ErrorCode.NOT_FOUND, "ingestion_event não encontrado")
        ds = db.get(DataSource, ie.data_source_id)
        auth = _AC(
            api_key_id=uuid.uuid4(),
            workspace_id=ie.workspace_id,
            workspace_slug="",
            data_source_id=ie.data_source_id,
            data_source_key=ds.key if ds else None,
            scopes=frozenset({"ingest"}),
        )
        # volta para pending para permitir o claim
        ie.status = PENDING
        raw = dict(ie.payload)
        db.commit()

    event = StackEvent.model_validate(raw)
    res = ingest_one(Session_, auth, event, raw)
    if res.status == "accepted":
        with Session_() as db:
            open_cases = db.execute(
                select(ResolutionCase).where(
                    ResolutionCase.ingestion_event_id == ie_id,
                    ResolutionCase.status.notin_(("resolved", "dismissed")),
                )
            ).scalars().all()
            for c in open_cases:
                c.status = "resolved"
                c.resolved_at = utcnow()
                c.resolved_by_type = "rule"
                c.resolution_action = "reprocessed"
            db.commit()
    return res

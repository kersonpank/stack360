"""Worker: lê `raw_evolution_messages` (banco legado, SÓ LEITURA) e projeta
no schema canônico `stack360` via `ingest_one()` — mesmo pipeline de 3
transações/idempotência que a API REST usa, chamado direto em Python (sem
round-trip HTTP; é processo interno confiável).

Não depende de `contacts`/`messages`/`contact_evidence`/`opportunities`
(legado, incompletos desde julho — ver docs/projection-whatsapp.md). Toda
identidade/observação é reextraída do texto bruto, só em mensagem RECEBIDA.

Uso:
    python -m app.stack360.projection.legacy_whatsapp \
        --workspace-slug stack360-empresas \
        --mode backfill --limit 100

    python -m app.stack360.projection.legacy_whatsapp \
        --workspace-slug stack360-empresas \
        --mode loop --interval 300
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.stack360.auth import AuthContext
from app.stack360.db import get_sessionmaker
from app.stack360.ingestion.gateway import ingest_one
from app.stack360.models.data_source import DataSource
from app.stack360.models.workspace import Workspace
from app.stack360.projection import legacy_rules as rules
from app.stack360.schemas.envelope import StackEvent
from app.stack360.security.hashing import sha256_hex

log = logging.getLogger("stack360.projection.legacy_whatsapp")

# Números das próprias instâncias — fato estrutural (são nossas linhas),
# não classificação. SuporteTSM ainda não confirmado (ver briefing 15/10).
OUR_INSTANCE_NUMBERS = {
    "+5599992027458",  # principal (MGSUPORTE / MesquitaGrupo)
    "+5511958098330",  # SP (sptransmesquita)
    # "+55...",  # TODO: confirmar dígitos do antigo SuporteTSM
}

MIN_VALID_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Conexão legada — somente leitura, sessão curta
# ---------------------------------------------------------------------------

def legacy_engine(database_url: str) -> Engine:
    return create_engine(
        database_url,
        connect_args={"options": "-c default_transaction_read_only=on"},
        pool_pre_ping=True,
    )


@dataclass
class RawMessage:
    external_message_id: str
    source_account_id: Optional[str]
    instance_name: Optional[str]
    whatsapp_message_id: Optional[str]
    remote_jid: Optional[str]
    participant: Optional[str]
    from_me: Optional[bool]
    push_name: Optional[str]
    message_type: Optional[str]
    message_datetime: Optional[datetime]
    loaded_at: Optional[datetime]
    raw_message: Optional[dict]
    text: Optional[str]


def _extract_text(raw_message: Optional[dict]) -> Optional[str]:
    """Texto da mensagem (Baileys/Evolution payload) — usado só em memória
    pra extração; NUNCA persistido no canônico (ver regra de privacidade)."""
    if not isinstance(raw_message, dict):
        return None
    for path in (
        ("conversation",),
        ("extendedTextMessage", "text"),
        ("imageMessage", "caption"),
        ("videoMessage", "caption"),
        ("documentMessage", "caption"),
    ):
        node: Any = raw_message
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, str) and node:
            return node
    return None


def iter_raw_messages(
    engine: Engine,
    *,
    since_loaded_at: Optional[datetime],
    overlap_hours: float = 3.0,
    batch_size: int = 500,
) -> Iterator[RawMessage]:
    """Cursor monotônico por `loaded_at` (inserção na origem) — NUNCA por
    `message_datetime`/occurred_at do canônico (mensagem histórica entrando
    depois do cursor atual ficaria presa pra sempre)."""
    cursor = since_loaded_at
    if cursor is not None:
        cursor = cursor - _hours(overlap_hours)

    with engine.connect() as conn:
        stmt = text(
            """
            SELECT external_message_id, source_account_id, instance_name,
                   whatsapp_message_id, remote_jid, participant, from_me,
                   push_name, message_type, message_datetime, loaded_at,
                   raw_message
            FROM raw_evolution_messages
            WHERE (:cursor IS NULL OR loaded_at > :cursor)
            ORDER BY loaded_at ASC
            LIMIT :limit
            """
        )
        rows = conn.execute(stmt, {"cursor": cursor, "limit": batch_size}).mappings().all()

    for row in rows:
        yield RawMessage(
            external_message_id=row["external_message_id"],
            source_account_id=row["source_account_id"],
            instance_name=row["instance_name"],
            whatsapp_message_id=row["whatsapp_message_id"],
            remote_jid=row["remote_jid"],
            participant=row["participant"],
            from_me=row["from_me"],
            push_name=row["push_name"],
            message_type=row["message_type"],
            message_datetime=row["message_datetime"],
            loaded_at=row["loaded_at"],
            raw_message=row["raw_message"],
            text=_extract_text(row["raw_message"]),
        )


def _hours(h: float):
    from datetime import timedelta

    return timedelta(hours=h)


# ---------------------------------------------------------------------------
# Resolução de sujeito / direção / filtros
# ---------------------------------------------------------------------------

def normalize_jid_to_e164(jid: Optional[str]) -> Optional[str]:
    if not jid:
        return None
    digits = "".join(ch for ch in jid.split("@")[0] if ch.isdigit())
    if not digits:
        return None
    return "+" + digits


def resolve_subject_jid(msg: RawMessage) -> Optional[str]:
    """1:1 -> a outra parte (remote_jid). Grupo -> o autor (participant)."""
    if rules.is_group_jid(msg.remote_jid):
        return msg.participant
    return msg.remote_jid


def is_our_number(e164: Optional[str]) -> bool:
    return bool(e164) and e164 in OUR_INSTANCE_NUMBERS


def should_process(msg: RawMessage) -> bool:
    if not rules.is_conversational_message(msg.message_type, msg.remote_jid):
        return False
    if msg.message_datetime is not None and msg.message_datetime < MIN_VALID_DATE:
        return False
    return True


# ---------------------------------------------------------------------------
# Construção de eventos StackEvent
# ---------------------------------------------------------------------------

def _event_id(*parts: str) -> str:
    return sha256_hex("|".join(parts))[:40]


def build_interaction_event(msg: RawMessage, subject_e164: Optional[str]) -> StackEvent:
    """Interação SEM o corpo da mensagem (regra de privacidade) — só
    metadados + referência ao bruto pra quem precisar consultar o texto."""
    direction = "outbound" if msg.from_me else "inbound"
    event_type = "interaction.message_sent" if msg.from_me else "interaction.message_received"
    identities = []
    if subject_e164 and not is_our_number(subject_e164):
        jid_type = "whatsapp_lid" if rules.is_lid(msg.remote_jid or "") else "whatsapp_jid"
        identities.append({"type": jid_type, "value": subject_e164})

    occurred_at = msg.message_datetime or msg.loaded_at or datetime.now(timezone.utc)
    return StackEvent(
        schema_version="1.0",
        event_id=f"msg:{msg.whatsapp_message_id or msg.external_message_id}",
        event_type=event_type,
        occurred_at=occurred_at,
        subject={"identities": identities} if identities else None,
        data={
            "channel": "whatsapp",
            "direction": direction,
            "message_type": msg.message_type,
            "has_media": msg.message_type not in (None, "conversation", "extendedTextMessage"),
            "external_interaction_id": msg.whatsapp_message_id or msg.external_message_id,
            "source_ref": f"{msg.instance_name}:{msg.external_message_id}",
            "push_name": msg.push_name,
        },
        context={"channel": "whatsapp", "direction": direction},
    )


def _observation_event(
    *,
    subject_e164: str,
    key: str,
    value: Any,
    confidence: float,
    source_kind: str,
    source_ref: str,
    occurred_at: datetime,
) -> StackEvent:
    return StackEvent(
        schema_version="1.0",
        event_id=_event_id("obs", subject_e164, key, str(value), source_ref),
        event_type="observation.recorded",
        occurred_at=occurred_at,
        subject={"identities": [{"type": "whatsapp_jid", "value": subject_e164}]},
        data={
            "key": key,
            "value": value,
            "confidence": confidence,
            "source_kind": source_kind,
            "source_ref": source_ref,
        },
    )


def _identity_event(
    *, subject_e164: str, identity_type: str, value: str, name_hint: Optional[str], occurred_at: datetime, source_ref: str
) -> StackEvent:
    return StackEvent(
        schema_version="1.0",
        event_id=_event_id("identity", subject_e164, identity_type, value, source_ref),
        event_type="identity.observed",
        occurred_at=occurred_at,
        subject={
            "identities": [
                {"type": "whatsapp_jid", "value": subject_e164},
                {"type": identity_type, "value": value},
            ]
        },
        data={"name": name_hint} if name_hint else {},
    )


_DO_NOT_CONTACT_TYPES = {"motorista", "fornecedor", "transportadora_parceira", "grupo"}


def build_extraction_events(msg: RawMessage, subject_e164: str) -> list[StackEvent]:
    """Só roda em mensagem RECEBIDA. Nunca emite identidade forte por CNPJ/
    e-mail simplesmente mencionado — só autodeclaração (regra corrigida)."""
    if not msg.text or is_our_number(subject_e164):
        return []

    occurred_at = msg.message_datetime or msg.loaded_at or datetime.now(timezone.utc)
    source_ref = f"{msg.instance_name}:{msg.external_message_id}"
    events: list[StackEvent] = []

    cnpjs = rules.extract_cnpjs(msg.text)
    self_cnpjs = set(rules.detect_self_declared_cnpjs(msg.text))
    for cnpj in set(cnpjs):
        events.append(
            _observation_event(
                subject_e164=subject_e164,
                key="mentioned_cnpj",
                value=cnpj,
                confidence=0.5,
                source_kind="extracted",
                source_ref=source_ref,
                occurred_at=occurred_at,
            )
        )
        if cnpj in self_cnpjs:
            events.append(
                _identity_event(
                    subject_e164=subject_e164,
                    identity_type="cnpj",
                    value=rules.normalize_cnpj_digits(cnpj) or cnpj,
                    name_hint=msg.push_name,
                    occurred_at=occurred_at,
                    source_ref=source_ref,
                )
            )

    emails = rules.extract_emails(msg.text)
    self_emails = set(rules.detect_self_declared_emails(msg.text))
    for email in set(emails):
        events.append(
            _observation_event(
                subject_e164=subject_e164,
                key="mentioned_email",
                value=email,
                confidence=0.5,
                source_kind="extracted",
                source_ref=source_ref,
                occurred_at=occurred_at,
            )
        )
        if email in self_emails and not rules.is_generic_webmail(email):
            events.append(
                _identity_event(
                    subject_e164=subject_e164,
                    identity_type="email",
                    value=email.lower(),
                    name_hint=msg.push_name,
                    occurred_at=occurred_at,
                    source_ref=source_ref,
                )
            )

    intents = rules.detect_intents(msg.text)
    vehicle_types = rules.detect_vehicle_types(msg.text)
    vehicle_bodies = rules.detect_vehicle_bodies(msg.text)
    roles = rules.detect_roles(msg.text)
    fretebras = rules.detect_fretebras(msg.text)

    if intents or vehicle_types or vehicle_bodies or roles or fretebras:
        events.append(
            _observation_event(
                subject_e164=subject_e164,
                key="whatsapp_signals",
                value={
                    "intents": intents,
                    "vehicle_types": vehicle_types,
                    "vehicle_bodies": vehicle_bodies,
                    "roles": roles,
                    "fretebras": bool(fretebras),
                },
                confidence=0.6,
                source_kind="extracted",
                source_ref=source_ref,
                occurred_at=occurred_at,
            )
        )

    tipo = _classify_relationship(intents, roles, vehicle_types, vehicle_bodies, bool(fretebras))
    if tipo:
        events.append(
            _observation_event(
                subject_e164=subject_e164,
                key="relationship.tsm",
                value=tipo,
                confidence=0.5,
                source_kind="legacy_classifier_rerun",
                source_ref=source_ref,
                occurred_at=occurred_at,
            )
        )
        if tipo in _DO_NOT_CONTACT_TYPES:
            events.append(
                _observation_event(
                    subject_e164=subject_e164,
                    key="policy.no_cold_outreach",
                    value=True,
                    confidence=0.5,
                    source_kind="derived",
                    source_ref=source_ref,
                    occurred_at=occurred_at,
                )
            )

    affiliation = rules.detect_self_declared_affiliation(msg.text)
    if affiliation:
        events.append(
            _observation_event(
                subject_e164=subject_e164,
                key="affiliation",
                value={"type": "internal", "empresa": affiliation},
                confidence=0.7,
                source_kind="self_declared",
                source_ref=source_ref,
                occurred_at=occurred_at,
            )
        )
    elif msg.from_me:
        # enviada_por_mim é evidência ESTRUTURAL de "nosso lado" — não precisa heurística.
        events.append(
            _observation_event(
                subject_e164=subject_e164,
                key="affiliation",
                value={"type": "internal", "empresa": None},
                confidence=0.9,
                source_kind="structural",
                source_ref=source_ref,
                occurred_at=occurred_at,
            )
        )

    return events


def _classify_relationship(intents, roles, vehicle_types, vehicle_bodies, fretebras: bool) -> Optional[str]:
    """Re-roda a classificação do legado (regra primeiro) sobre o texto
    reextraído — resultado é SEMPRE crença (observation), nunca funil."""
    has_vehicle = bool(vehicle_types or vehicle_bodies)
    is_motorista = "motorista" in roles or "motorista" in intents or (
        "disponibilidade" in intents and has_vehicle
    ) or fretebras
    if is_motorista:
        return "motorista"
    is_fornecedor = has_vehicle and any(i in intents for i in ("cotacao", "valor", "frete"))
    if is_fornecedor:
        return "fornecedor"
    if any(i in intents for i in ("cotacao", "valor", "frete")):
        return "lead"
    return None


# ---------------------------------------------------------------------------
# Emissão (ingest_one direto em Python)
# ---------------------------------------------------------------------------

def make_auth_context(workspace_id: uuid.UUID, workspace_slug: str, data_source_id: uuid.UUID, data_source_key: str) -> AuthContext:
    return AuthContext(
        api_key_id=uuid.uuid4(),  # processo interno — não referencia ApiKey real
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        data_source_id=data_source_id,
        data_source_key=data_source_key,
        scopes=frozenset({"ingest"}),
    )


def emit(Session_, auth: AuthContext, event: StackEvent) -> None:
    res = ingest_one(Session_, auth, event, event.model_dump(mode="json"))
    if res.status == "error" and res.error is not None:
        log.warning("evento %s falhou: %s", event.event_id, res.error.message)


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def _resolve_workspace_and_sources(db: Session, workspace_slug: str) -> tuple[Workspace, dict[str, DataSource]]:
    w = db.execute(select(Workspace).where(Workspace.slug == workspace_slug)).scalar_one_or_none()
    if w is None:
        sys.exit(f"workspace '{workspace_slug}' não existe — crie via /settings/api-keys antes")
    sources = db.execute(select(DataSource).where(DataSource.workspace_id == w.id)).scalars().all()
    by_instance = {s.key: s for s in sources}
    return w, by_instance


def run_batch(
    *,
    legacy_url: str,
    workspace_slug: str,
    limit: Optional[int],
    since_loaded_at: Optional[datetime],
) -> int:
    Session_ = get_sessionmaker()
    with Session_() as db:
        workspace, sources_by_instance = _resolve_workspace_and_sources(db, workspace_slug)

    eng = legacy_engine(legacy_url)
    processed = 0
    skipped_date = 0
    skipped_filter = 0
    seen_whatsapp_ids: set[str] = set()

    try:
        for msg in iter_raw_messages(eng, since_loaded_at=since_loaded_at, batch_size=limit or 500):
            if limit and processed >= limit:
                break
            if not should_process(msg):
                if msg.message_datetime and msg.message_datetime < MIN_VALID_DATE:
                    skipped_date += 1
                else:
                    skipped_filter += 1
                continue

            wa_id = msg.whatsapp_message_id or msg.external_message_id
            if wa_id in seen_whatsapp_ids:
                continue  # dedup entre instâncias (mesmo grupo, 2 contas nossas)
            seen_whatsapp_ids.add(wa_id)

            instance_key = (msg.instance_name or "unknown").lower()
            source = sources_by_instance.get(instance_key)
            if source is None:
                log.warning("sem DataSource pra instância '%s' — pulando mensagem", instance_key)
                continue

            auth = make_auth_context(workspace.id, workspace.slug, source.id, source.key)
            subject_e164 = normalize_jid_to_e164(resolve_subject_jid(msg))
            if not subject_e164:
                continue

            emit(Session_, auth, build_interaction_event(msg, subject_e164))

            # Extração completa (CNPJ/e-mail/intent/relacionamento) só em mensagem
            # recebida. Mensagem enviada só gera a observação estrutural de
            # afiliação ("enviada_por_mim" já prova "nosso lado").
            for event in build_extraction_events(msg, subject_e164):
                if msg.from_me and event.data.get("key") != "affiliation":
                    continue
                emit(Session_, auth, event)

            processed += 1
    finally:
        eng.dispose()

    log.info(
        "lote concluído: %d processadas, %d descartadas (data<2020), %d descartadas (filtro)",
        processed, skipped_date, skipped_filter,
    )
    return processed


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="app.stack360.projection.legacy_whatsapp")
    p.add_argument("--workspace-slug", required=True)
    p.add_argument("--legacy-database-url", default=None, help="default: env DATABASE_URL")
    p.add_argument("--mode", choices=["backfill", "loop"], default="backfill")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--interval", type=int, default=300)
    args = p.parse_args(argv)

    import os

    legacy_url = args.legacy_database_url or os.environ.get("DATABASE_URL")
    if not legacy_url:
        sys.exit("faltou --legacy-database-url ou env DATABASE_URL")

    if args.mode == "backfill":
        run_batch(legacy_url=legacy_url, workspace_slug=args.workspace_slug, limit=args.limit, since_loaded_at=None)
        return

    # loop: incremental, cursor = loaded_at da última mensagem processada
    cursor: Optional[datetime] = None
    while True:
        try:
            run_batch(legacy_url=legacy_url, workspace_slug=args.workspace_slug, limit=None, since_loaded_at=cursor)
            cursor = datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001
            log.exception("erro no ciclo do loop — tenta de novo no próximo intervalo")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

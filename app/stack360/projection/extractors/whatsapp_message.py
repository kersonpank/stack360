"""Extractor — `SourceEnvelope` (envelope_type="whatsapp.message") -> eventos
canônicos. Mesma lógica que já existia (regras de identidade/privacidade
aprovadas), só realocada: a camada 1 (reader) não sabe de regra nenhuma, essa
camada 2 não sabe ler banco nenhum.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.stack360.projection import legacy_rules as rules
from app.stack360.projection.envelope import SourceEnvelope
from app.stack360.projection.extractors.base import register
from app.stack360.projection.readers.whatsapp_legacy import ENVELOPE_TYPE
from app.stack360.schemas.envelope import StackEvent
from app.stack360.security.hashing import sha256_hex

MIN_VALID_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)

# Números das próprias instâncias — fato estrutural (nossas linhas), não
# classificação. SuporteTSM ainda não confirmado (ver briefing 15/10).
OUR_INSTANCE_NUMBERS = {
    "+5599992027458",  # principal (MGSUPORTE / MesquitaGrupo)
    "+5511958098330",  # SP (sptransmesquita)
    # "+55...",  # TODO: confirmar dígitos do antigo SuporteTSM
}

_DO_NOT_CONTACT_TYPES = {"motorista", "fornecedor", "transportadora_parceira", "grupo"}


def is_our_number(e164: Optional[str]) -> bool:
    return bool(e164) and e164 in OUR_INSTANCE_NUMBERS


def normalize_jid_to_e164(jid: Optional[str]) -> Optional[str]:
    if not jid:
        return None
    digits = "".join(ch for ch in jid.split("@")[0] if ch.isdigit())
    return "+" + digits if digits else None


def resolve_subject_jid(content: dict) -> Optional[str]:
    """1:1 -> a outra parte. Grupo -> o autor (participant), nunca o grupo."""
    remote_jid = content.get("remote_jid")
    if rules.is_group_jid(remote_jid):
        return content.get("participant")
    return remote_jid


def _message_text(raw_message: Optional[dict]) -> Optional[str]:
    """Texto só em memória pra extração — NUNCA persistido no canônico."""
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
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, str) and node:
            return node
    return None


def _is_conversational(content: dict, captured_at: datetime) -> bool:
    if not rules.is_conversational_message(content.get("message_type"), content.get("remote_jid")):
        return False
    if captured_at < MIN_VALID_DATE:
        return False
    return True


def _event_id(*parts: str) -> str:
    return sha256_hex("|".join(parts))[:40]


def _build_interaction_event(envelope: SourceEnvelope, content: dict, subject_e164: str) -> StackEvent:
    from_me = bool(content.get("from_me"))
    direction = "outbound" if from_me else "inbound"
    event_type = "interaction.message_sent" if from_me else "interaction.message_received"

    identities = []
    if subject_e164 and not is_our_number(subject_e164):
        remote_jid = content.get("remote_jid") or ""
        jid_type = "whatsapp_lid" if rules.is_lid(remote_jid) else "whatsapp_jid"
        identities.append({"type": jid_type, "value": subject_e164})

    return StackEvent(
        schema_version="1.0",
        event_id=f"msg:{envelope.external_key}",
        event_type=event_type,
        occurred_at=envelope.captured_at,
        subject={"identities": identities} if identities else None,
        data={
            "channel": "whatsapp",
            "direction": direction,
            "message_type": content.get("message_type"),
            "has_media": content.get("message_type") not in (None, "conversation", "extendedTextMessage"),
            "external_interaction_id": envelope.external_key,
            "source_ref": f"{envelope.source_key}:{envelope.external_key}",
            "push_name": content.get("push_name"),
        },
        context={"channel": "whatsapp", "direction": direction},
    )


def _observation_event(*, subject_e164, key, value, confidence, source_kind, source_ref, occurred_at) -> StackEvent:
    return StackEvent(
        schema_version="1.0",
        event_id=_event_id("obs", subject_e164, key, str(value), source_ref),
        event_type="observation.recorded",
        occurred_at=occurred_at,
        subject={"identities": [{"type": "whatsapp_jid", "value": subject_e164}]},
        data={"key": key, "value": value, "confidence": confidence, "source_kind": source_kind, "source_ref": source_ref},
    )


def _identity_event(*, subject_e164, identity_type, value, name_hint, occurred_at, source_ref) -> StackEvent:
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


def _classify_relationship(intents, roles, vehicle_types, vehicle_bodies, fretebras: bool) -> Optional[str]:
    has_vehicle = bool(vehicle_types or vehicle_bodies)
    is_motorista = (
        "motorista" in roles
        or "motorista" in intents
        or ("disponibilidade" in intents and has_vehicle)
        or fretebras
    )
    if is_motorista:
        return "motorista"
    if has_vehicle and any(i in intents for i in ("cotacao", "valor", "frete")):
        return "fornecedor"
    if any(i in intents for i in ("cotacao", "valor", "frete")):
        return "lead"
    return None


def _build_extraction_events(content: dict, text: Optional[str], subject_e164: str, occurred_at: datetime, source_ref: str) -> list[StackEvent]:
    if not text or is_our_number(subject_e164):
        return []

    events: list[StackEvent] = []
    push_name = content.get("push_name")

    cnpjs = rules.extract_cnpjs(text)
    self_cnpjs = set(rules.detect_self_declared_cnpjs(text))
    for cnpj in set(cnpjs):
        events.append(_observation_event(subject_e164=subject_e164, key="mentioned_cnpj", value=cnpj, confidence=0.5, source_kind="extracted", source_ref=source_ref, occurred_at=occurred_at))
        if cnpj in self_cnpjs:
            events.append(_identity_event(subject_e164=subject_e164, identity_type="cnpj", value=rules.normalize_cnpj_digits(cnpj) or cnpj, name_hint=push_name, occurred_at=occurred_at, source_ref=source_ref))

    emails = rules.extract_emails(text)
    self_emails = set(rules.detect_self_declared_emails(text))
    for email in set(emails):
        events.append(_observation_event(subject_e164=subject_e164, key="mentioned_email", value=email, confidence=0.5, source_kind="extracted", source_ref=source_ref, occurred_at=occurred_at))
        if email in self_emails and not rules.is_generic_webmail(email):
            events.append(_identity_event(subject_e164=subject_e164, identity_type="email", value=email.lower(), name_hint=push_name, occurred_at=occurred_at, source_ref=source_ref))

    intents = rules.detect_intents(text)
    vehicle_types = rules.detect_vehicle_types(text)
    vehicle_bodies = rules.detect_vehicle_bodies(text)
    roles = rules.detect_roles(text)
    fretebras = rules.detect_fretebras(text)

    if intents or vehicle_types or vehicle_bodies or roles or fretebras:
        events.append(_observation_event(
            subject_e164=subject_e164, key="whatsapp_signals",
            value={"intents": intents, "vehicle_types": vehicle_types, "vehicle_bodies": vehicle_bodies, "roles": roles, "fretebras": bool(fretebras)},
            confidence=0.6, source_kind="extracted", source_ref=source_ref, occurred_at=occurred_at,
        ))

    tipo = _classify_relationship(intents, roles, vehicle_types, vehicle_bodies, bool(fretebras))
    if tipo:
        events.append(_observation_event(subject_e164=subject_e164, key="relationship.tsm", value=tipo, confidence=0.5, source_kind="legacy_classifier_rerun", source_ref=source_ref, occurred_at=occurred_at))
        if tipo in _DO_NOT_CONTACT_TYPES:
            events.append(_observation_event(subject_e164=subject_e164, key="policy.no_cold_outreach", value=True, confidence=0.5, source_kind="derived", source_ref=source_ref, occurred_at=occurred_at))

    affiliation = rules.detect_self_declared_affiliation(text)
    if affiliation:
        events.append(_observation_event(subject_e164=subject_e164, key="affiliation", value={"type": "internal", "empresa": affiliation}, confidence=0.7, source_kind="self_declared", source_ref=source_ref, occurred_at=occurred_at))
    elif content.get("from_me"):
        events.append(_observation_event(subject_e164=subject_e164, key="affiliation", value={"type": "internal", "empresa": None}, confidence=0.9, source_kind="structural", source_ref=source_ref, occurred_at=occurred_at))

    return events


@register(ENVELOPE_TYPE)
def extract(envelope: SourceEnvelope) -> list[StackEvent]:
    content = envelope.content
    if not _is_conversational(content, envelope.captured_at):
        return []

    subject_e164 = normalize_jid_to_e164(resolve_subject_jid(content))
    if not subject_e164:
        return []

    source_ref = f"{envelope.source_key}:{envelope.external_key}"
    events = [_build_interaction_event(envelope, content, subject_e164)]

    text = _message_text(content.get("raw_message"))
    from_me = bool(content.get("from_me"))
    for event in _build_extraction_events(content, text, subject_e164, envelope.captured_at, source_ref):
        if from_me and event.data.get("key") != "affiliation":
            continue
        events.append(event)

    return events

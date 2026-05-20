"""
Build contact_evidence rows from detected signals.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _make_evidence(
    contact_id: str,
    evidence_type: str,
    evidence_value: str,
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
    confidence: float = 0.9,
    source: str = "rules",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "evidence_type": evidence_type,
        "evidence_value": evidence_value,
        "confidence": confidence,
        "source": source,
        "payload": payload or {},
        "created_at": datetime.now(tz=timezone.utc),
    }


def build_evidence_rows(
    contact_id: str,
    conversation_id: Optional[str],
    cnpjs: List[str],
    cpfs: List[str],
    placas: List[str],
    emails: List[str],
    vehicle_types: List[str],
    vehicle_bodies: List[str],
    intents: List[str],
    roles: List[str],
    routes: List[str],
    tipo_relacionamento: str,
    message_id: Optional[str] = None,
    fretebras_matches: Optional[List[str]] = None,
    fretebras_payload: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    rows = []

    for val in cnpjs:
        rows.append(_make_evidence(contact_id, "cnpj", val, conversation_id, message_id))
    for val in cpfs:
        rows.append(_make_evidence(contact_id, "cpf", val, conversation_id, message_id))
    for val in placas:
        rows.append(_make_evidence(contact_id, "placa", val, conversation_id, message_id))
    for val in emails:
        rows.append(_make_evidence(contact_id, "email", val, conversation_id, message_id))
    for val in vehicle_types:
        rows.append(_make_evidence(contact_id, "vehicle_type", val, conversation_id, message_id))
    for val in vehicle_bodies:
        rows.append(_make_evidence(contact_id, "vehicle_body", val, conversation_id, message_id))
    for val in intents:
        rows.append(_make_evidence(contact_id, "intent", val, conversation_id, message_id, confidence=0.8))
    for val in roles:
        rows.append(_make_evidence(contact_id, "role", val, conversation_id, message_id, confidence=0.8))
    for val in routes:
        rows.append(_make_evidence(contact_id, "route", val, conversation_id, message_id, confidence=0.7))
    if tipo_relacionamento and tipo_relacionamento not in ("desconhecido", "unknown"):
        rows.append(_make_evidence(contact_id, "tipo_relacionamento", tipo_relacionamento, conversation_id, message_id, confidence=0.75))

    if fretebras_matches:
        payload_sd = fretebras_payload or {}
        payload_sd = {
            "matched_text": fretebras_matches[0],
            "all_matches": fretebras_matches[:5],
            "rule": "fretebras_domain_motorista",
            "motivo": "Presença de fretebras.com na conversa indica alta probabilidade de motorista.",
            **payload_sd,
        }
        rows.append(_make_evidence(
            contact_id, "source_domain", "fretebras",
            conversation_id, message_id,
            confidence=0.98,
            source="rules",
            payload=payload_sd,
        ))
        rows.append(_make_evidence(
            contact_id, "role", "motorista",
            conversation_id, message_id,
            confidence=0.98,
            source="rules",
            payload={
                "reason": "fretebras.com detectado na conversa",
                "rule": "fretebras_domain_motorista",
            },
        ))

    return rows

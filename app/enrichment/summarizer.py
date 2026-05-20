"""
Template-based summary generation (no LLM required).
Produces human-readable strings from structured signals.
"""
from typing import List


def build_contact_summary(
    contact_id: str,
    total_messages: int,
    total_conversations: int,
    tipo_relacionamento: str,
    intents: List[str],
    tags: List[str],
    vehicle_types: List[str],
    vehicle_bodies: List[str],
    fretebras_detected: bool = False,
) -> str:
    parts = [
        f"Stakeholder com {total_messages} mensagens em {total_conversations} conversa(s)."
    ]

    if tipo_relacionamento and tipo_relacionamento not in ("desconhecido", "unknown"):
        parts.append(f"Classificado como {tipo_relacionamento}.")

    if intents:
        intent_str = ", ".join(intents[:5])
        parts.append(f"Sinais detectados: {intent_str}.")

    if vehicle_types:
        v = ", ".join(vehicle_types[:3])
        parts.append(f"Veículos mencionados: {v}.")

    if vehicle_bodies:
        b = ", ".join(vehicle_bodies[:3])
        parts.append(f"Tipos de carroceria: {b}.")

    semantic_tags = [t for t in tags if t not in {"whatsapp", "grupo"}]
    if semantic_tags:
        parts.append(f"Tags detectadas: {', '.join(semantic_tags[:8])}.")

    if fretebras_detected:
        parts.append("Classificado como motorista por presença de Fretebras na conversa.")

    return " ".join(parts)


def build_conversation_summary(
    conversation_id: str,
    total_messages: int,
    dominant_intents: List[str],
) -> str:
    parts = [f"Conversa com {total_messages} mensagem(s)."]
    if dominant_intents:
        parts.append(f"Tópicos principais: {', '.join(dominant_intents[:4])}.")
    return " ".join(parts)


def build_conversation_subject(intents: List[str], vehicle_types: List[str]) -> str:
    """Return short string for assunto_principal."""
    if not intents and not vehicle_types:
        return "geral"
    top = (intents[:2] + vehicle_types[:1])[:3]
    return "/".join(top) if top else "geral"

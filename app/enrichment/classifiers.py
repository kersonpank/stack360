"""
Classify tipo_relacionamento and derive tags from detected signals.
"""
from typing import List

# Specificity order — higher rank = more specific classification.
# Never downgrade a contact to a lower-ranked type.
_SPECIFICITY = {
    "desconhecido": 0,
    "lead": 1,
    "fornecedor": 2,
    "motorista": 3,
    "cliente": 4,
    "grupo": 5,
}


def should_update_tipo(current: str, new: str) -> bool:
    """Return True if new tipo is equally or more specific than current."""
    return _SPECIFICITY.get(new, 0) >= _SPECIFICITY.get(current, 0)


def classify_tipo_relacionamento(
    contact_id: str,
    intents: List[str],
    roles: List[str],
    vehicle_types: List[str],
    vehicle_bodies: List[str],
    total_messages: int,
    total_conversations: int,
    placas: List[str] = None,
    fretebras_detected: bool = False,
) -> str:
    """
    Returns the best-fit tipo_relacionamento string.
    Priority (highest first): grupo > cliente > motorista > fornecedor > lead > desconhecido

    Confidence thresholds (implemented via signal strength):
      - grupo:     structural (contact_id prefix) — always certain
      - cliente:   >= 3 conversations + >= 20 messages + operacao signals
      - motorista: >= 0.70 — specific role/intent OR (disponibilidade + vehicle)
      - fornecedor: >= 0.65 — vehicle + pricing intent AND NOT motorista
      - lead:       >= 0.60 — any pricing/quote intent
    """
    placas = placas or []

    if contact_id.startswith("group:"):
        return "grupo"

    # cliente: recurrent operational contact (strongest non-group signal)
    is_recorrente = total_conversations >= 3 and total_messages >= 20
    has_operacao_signals = any(i in intents for i in ["coleta", "frete", "entrega", "carga"])
    if is_recorrente and has_operacao_signals:
        return "cliente"

    # motorista: requires specific driver signal (confidence >= 0.70)
    has_explicit_motorista = "motorista" in roles or "motorista" in intents
    has_vehicle_availability = "disponibilidade" in intents and (vehicle_types or vehicle_bodies)
    has_placa_vehicle = bool(placas) and (vehicle_types or vehicle_bodies)
    # fretebras.com presence = high-confidence motorista (0.98)
    is_motorista = has_explicit_motorista or has_vehicle_availability or has_placa_vehicle or fretebras_detected

    # fornecedor: offers vehicles + pricing, but NOT a personal driver (confidence >= 0.65)
    is_fornecedor = (
        (vehicle_types or vehicle_bodies)
        and not is_motorista
        and any(i in intents for i in ["cotacao", "valor", "frete"])
    )

    if is_motorista:
        return "motorista"

    if is_fornecedor:
        return "fornecedor"

    # lead: any pricing/quote interest (confidence >= 0.60)
    if any(i in intents for i in ["cotacao", "valor", "frete"]):
        return "lead"

    return "desconhecido"


def build_tags(
    contact_id: str,
    intents: List[str],
    roles: List[str],
    vehicle_types: List[str],
    vehicle_bodies: List[str],
    cnpjs: List[str],
    cpfs: List[str],
    placas: List[str],
    source_accounts: List[str],
    existing_tags: List[str],
    tipo_relacionamento: str = "",
    fretebras_detected: bool = False,
) -> List[str]:
    """Build deduplicated tag list from detected signals."""
    tags = set(existing_tags or [])
    tags.add("whatsapp")

    if contact_id.startswith("group:"):
        tags.add("grupo")

    if fretebras_detected:
        tags.add("fretebras")
        tags.add("motorista")

    # intents → tags
    for intent in intents:
        tags.add(intent)

    # roles → tags
    for role in roles:
        tags.add(role)

    # vehicle presence
    if vehicle_types or vehicle_bodies:
        tags.add("veiculo")

    # document presence
    if cnpjs:
        tags.add("documento")
        tags.add("cnpj")
    if cpfs:
        tags.add("documento")
        tags.add("cpf")
    if placas:
        tags.add("documento")
        tags.add("placa")

    # multi-channel
    if len(set(source_accounts)) > 1:
        tags.add("multicanal")

    # tipo_relacionamento-derived tags
    if tipo_relacionamento and tipo_relacionamento not in {"desconhecido", "grupo"}:
        tags.add(tipo_relacionamento)  # adds "motorista", "lead", "cliente", "fornecedor"

    if tipo_relacionamento == "cliente":
        tags.add("cliente_potencial")

    return sorted(tags)

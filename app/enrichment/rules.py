"""
Deterministic rule-based extractors for WhatsApp business messages.
Returns typed matches — no side effects.
"""
import re
from typing import List, Optional


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

_CNPJ_RE = re.compile(r"\b\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}\b")
_CPF_RE = re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}(?!\d)\b")
_PLACA_RE = re.compile(r"\b[A-Z]{3}[-\s]?\d[A-Z0-9]\d{2}\b", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")


def extract_cnpjs(text: str) -> List[str]:
    return _CNPJ_RE.findall(text or "")


def extract_cpfs(text: str) -> List[str]:
    return _CPF_RE.findall(text or "")


def extract_placas(text: str) -> List[str]:
    return _PLACA_RE.findall(text or "")


def extract_emails(text: str) -> List[str]:
    return _EMAIL_RE.findall(text or "")


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

_VEHICLE_TYPES = [
    "carreta", "truck", "fiorino", "toco", r"3/4", "van", "bitrem",
    "rodotrem", "VUC", "caminhão", "caminhao",
]

_VEHICLE_BODIES = [
    "baú", "bau", "sider", "graneleiro", "grade baixa", "grade-baixa",
    "refrigerado", "prancha", "cegonha", "munck", "guindaste", "basculante",
    "tanque", "caçamba", "cacamba",
]

def _build_keyword_pattern(keywords: List[str]) -> re.Pattern:
    if not keywords:
        raise ValueError("keywords list must not be empty")
    escaped = sorted([re.escape(k) for k in keywords], key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(escaped) + r")(?!\w)", re.IGNORECASE)


_VEHICLE_TYPE_RE = _build_keyword_pattern(_VEHICLE_TYPES)
_VEHICLE_BODY_RE = _build_keyword_pattern(_VEHICLE_BODIES)


def detect_vehicle_types(text: str) -> List[str]:
    return list(set(m.lower() for m in _VEHICLE_TYPE_RE.findall(text or "")))


def detect_vehicle_bodies(text: str) -> List[str]:
    return list(set(m.lower() for m in _VEHICLE_BODY_RE.findall(text or "")))


# ---------------------------------------------------------------------------
# Intents
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS = {
    "cotacao": ["cotação", "cotacao", "cotar", "orçamento", "orcamento", "orçar"],
    "coleta": ["coleta", "coletar", "buscar", "busca", "apanhar"],
    "frete": ["frete", "fretes", "transporte", "transportar"],
    "entrega": ["entrega", "entregar", "delivery"],
    "disponibilidade": ["disponível", "disponivel", "disponibilidade", "livre", "vaga"],
    "motorista": ["motorista", "motoristas", "condutor"],
    "carga": ["carga", "cargas", "mercadoria", "mercadorias"],
    "descarga": ["descarga", "descarregar", "descarregamento"],
    "nota_fiscal": ["nota fiscal", "NF", "nota", "NF-e", "NFe"],
    "comprovante": ["comprovante", "comprovantes", "recibo"],
    "pagamento": ["pagamento", "pagar", "pagamentos", "boleto", "PIX", "transferência"],
    "reclamacao": ["reclamação", "reclamacao", "problema", "problemas", "queixa", "insatisfeito"],
    "atraso": ["atraso", "atrasado", "atrasados", "atrasou", "demora", "demorou"],
    "suporte": ["suporte", "ajuda", "auxílio", "auxilio"],
    "valor": ["valor", "valores", "preço", "preco", "preços", "precos", "quanto"],
    "rota": ["rota", "rotas", "trajeto", "percurso"],
}

def _build_intent_patterns(intent_map: dict) -> dict:
    patterns = {}
    for intent, keywords in intent_map.items():
        escaped = sorted([re.escape(k) for k in keywords], key=len, reverse=True)
        patterns[intent] = re.compile(
            r"(?<!\w)(" + "|".join(escaped) + r")(?!\w)", re.IGNORECASE
        )
    return patterns


_INTENT_PATTERNS = _build_intent_patterns(_INTENT_KEYWORDS)


def detect_intents(text: str) -> List[str]:
    """Return list of detected intent keys present in text."""
    found = []
    t = text or ""
    for intent, pat in _INTENT_PATTERNS.items():
        if pat.search(t):
            found.append(intent)
    return found


# ---------------------------------------------------------------------------
# Routes (simple heuristic: city/UF pairs or "de X para Y" patterns)
# ---------------------------------------------------------------------------

_ROUTE_RE = re.compile(
    r"(?:de\s+([A-ZÀ-Ú][a-zA-ZÀ-ú\s]{2,20})\s+(?:para|p/|até)\s+([A-ZÀ-Ú][a-zA-ZÀ-ú\s]{2,20}))",
    re.IGNORECASE,
)

def extract_routes(text: str) -> List[str]:
    """Return list of 'origem → destino' strings detected."""
    matches = _ROUTE_RE.findall(text or "")
    return [f"{o.strip()} → {d.strip()}" for o, d in matches]


# ---------------------------------------------------------------------------
# Domain signals
# ---------------------------------------------------------------------------

_FRETEBRAS_RE = re.compile(
    r"(?:https?://)?(?:www\.)?fretebras\.com(?:\.br)?(?:/\S*)?",
    re.IGNORECASE,
)


def detect_fretebras(text: str) -> List[str]:
    """Return deduplicated list of fretebras domain mentions/URLs found in text."""
    return list(set(_FRETEBRAS_RE.findall(text or "")))


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

_ROLE_KEYWORDS = {
    "motorista": ["motorista", "condutor", "chofer"],
    "financeiro": ["financeiro", "cobrança", "cobranca", "pagamento", "boleto"],
    "suporte": ["suporte", "atendimento", "SAC"],
    "grupo": [],  # detected by contact_id prefix, not text
    "lead": ["cotação", "cotacao", "orçamento", "orcamento", "quanto custa", "preço"],
}

_ROLE_PATTERNS = {
    role: _build_keyword_pattern(kws)
    for role, kws in _ROLE_KEYWORDS.items()
    if kws
}


def detect_roles(text: str, contact_id: str = "") -> List[str]:
    found = []
    if contact_id.startswith("group:"):
        found.append("grupo")
        return found
    t = text or ""
    for role, pat in _ROLE_PATTERNS.items():
        if pat.search(t):
            found.append(role)
    return list(set(found))

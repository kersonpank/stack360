"""Regras determinísticas pra ler WhatsApp bruto (raw_evolution_messages) e
projetar no schema canônico `stack360`.

Os extratores de CNPJ/CPF/placa/e-mail/veículo/intent abaixo são uma CÓPIA
deliberada (não import) de `app/enrichment/rules.py` e
`app/enrichment/classifiers.py` — código do app legado, que será aposentado.
Copiados em 2026-10-16. A lógica de regex em si está correta; a falha do
legado foi aplicá-la sem direção (enviada/recebida) e sem excluir número e
domínio nossos — por isso este módulo só roda extração em mensagem RECEBIDA
e sempre com `external_message_id` de proveniência (ver `legacy_whatsapp.py`).

Diferença chave em relação ao legado: aqui CNPJ/e-mail extraídos NUNCA viram
identidade automaticamente — viram Observation fraca. Promoção a identidade
forte exige autodeclaração explícita ou repetição corroborada (ver
`detect_self_declared_cnpj`/`detect_self_declared_email` e o passo de
promoção em `legacy_whatsapp.py`).
"""
from __future__ import annotations

import re
from typing import List, Optional

# ---------------------------------------------------------------------------
# Documentos (cópia de app/enrichment/rules.py)
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


def normalize_cnpj_digits(raw: str) -> Optional[str]:
    d = re.sub(r"\D", "", raw or "")
    return d if len(d) == 14 else None


def cnpj_root(cnpj_digits: str) -> Optional[str]:
    """Raiz do CNPJ (8 primeiros dígitos) — identifica matriz/filiais da mesma empresa."""
    d = re.sub(r"\D", "", cnpj_digits or "")
    return d[:8] if len(d) == 14 else None


# ---------------------------------------------------------------------------
# Veículos (cópia de app/enrichment/rules.py)
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
# Intents (cópia de app/enrichment/rules.py)
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
        patterns[intent] = re.compile(r"(?<!\w)(" + "|".join(escaped) + r")(?!\w)", re.IGNORECASE)
    return patterns


_INTENT_PATTERNS = _build_intent_patterns(_INTENT_KEYWORDS)


def detect_intents(text: str) -> List[str]:
    found = []
    t = text or ""
    for intent, pat in _INTENT_PATTERNS.items():
        if pat.search(t):
            found.append(intent)
    return found


# ---------------------------------------------------------------------------
# Papéis / fretebras (cópia de app/enrichment/rules.py)
# ---------------------------------------------------------------------------

_FRETEBRAS_RE = re.compile(r"(?:https?://)?(?:www\.)?fretebras\.com(?:\.br)?(?:/\S*)?", re.IGNORECASE)


def detect_fretebras(text: str) -> List[str]:
    return list(set(_FRETEBRAS_RE.findall(text or "")))


_ROLE_KEYWORDS = {
    "motorista": ["motorista", "condutor", "chofer"],
    "financeiro": ["financeiro", "cobrança", "cobranca", "pagamento", "boleto"],
    "suporte": ["suporte", "atendimento", "SAC"],
}

_ROLE_PATTERNS = {role: _build_keyword_pattern(kws) for role, kws in _ROLE_KEYWORDS.items() if kws}


def detect_roles(text: str) -> List[str]:
    found = []
    t = text or ""
    for role, pat in _ROLE_PATTERNS.items():
        if pat.search(t):
            found.append(role)
    return list(set(found))


# ---------------------------------------------------------------------------
# NOVO — autodeclaração (não existe no legado). Exige marcador possessivo
# ("meu"/"nosso"/...) perto do valor, dito pelo PRÓPRIO autor sobre si mesmo.
# Isso distingue "meu CNPJ é X" (autodeclaração) de "a cotação é pro CNPJ X"
# (menção de terceiro — fica sempre fraco).
# ---------------------------------------------------------------------------

_SELF_MARKER = r"(?:meu|minha|nosso|nossa|da\s+minha\s+empresa|aqui\s+(?:é|e)\s+da)"
_CNPJ_GROUP = r"(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})"
_EMAIL_GROUP = r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"

_SELF_CNPJ_RE = re.compile(
    rf"\b{_SELF_MARKER}\b[^.\n]{{0,25}}?\bcnpj\b[^.\n]{{0,10}}?{_CNPJ_GROUP}",
    re.IGNORECASE,
)

_SELF_EMAIL_RE = re.compile(
    rf"\b{_SELF_MARKER}\b[^.\n]{{0,25}}?\be-?mail\b[^.\n]{{0,10}}?{_EMAIL_GROUP}",
    re.IGNORECASE,
)


def detect_self_declared_cnpjs(text: str) -> List[str]:
    """CNPJs que o autor declarou como PRÓPRIO (regra de promoção a/b, parte 'autodeclaração')."""
    return _SELF_CNPJ_RE.findall(text or "")


def detect_self_declared_emails(text: str) -> List[str]:
    """E-mails que o autor declarou como PRÓPRIO."""
    return _SELF_EMAIL_RE.findall(text or "")


_AFFILIATION_RE = re.compile(
    r"\b(?:aqui\s+(?:é|e)\s+da|equipe|time)\s+([A-ZÀ-Ú][\wÀ-ú]{2,30})",
    re.IGNORECASE,
)


def detect_self_declared_affiliation(text: str) -> Optional[str]:
    """Nome de empresa que o autor citou como a própria ('aqui é da TSM')."""
    m = _AFFILIATION_RE.search(text or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# NOVO — domínios de webmail genérico nunca promovem a identidade forte,
# mesmo autodeclarados (pessoa física comum não prova vínculo corporativo).
# ---------------------------------------------------------------------------

GENERIC_WEBMAIL_DOMAINS = frozenset(
    {
        "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.br",
        "icloud.com", "live.com", "bol.com.br", "uol.com.br", "terra.com.br",
        "msn.com", "ig.com.br", "globo.com", "r7.com",
    }
)


def is_generic_webmail(email: str) -> bool:
    domain = (email or "").rsplit("@", 1)[-1].strip().lower()
    return domain in GENERIC_WEBMAIL_DOMAINS


# ---------------------------------------------------------------------------
# NOVO — filtro de mensagem: tipos que não são conversa real.
# ---------------------------------------------------------------------------

_NON_CONVERSATION_MESSAGE_TYPES = frozenset(
    {
        "reactionMessage", "protocolMessage", "senderKeyDistributionMessage",
        "call", "pollUpdateMessage", "pollCreationMessage",
    }
)


def is_conversational_message(message_type: Optional[str], remote_jid: Optional[str]) -> bool:
    """False = descarta do pipeline (status, newsletter, reação, protocolo, chamada)."""
    jid = (remote_jid or "").lower()
    if jid.endswith("@broadcast") or jid.endswith("@newsletter"):
        return False
    if (message_type or "") in _NON_CONVERSATION_MESSAGE_TYPES:
        return False
    return True


def is_group_jid(remote_jid: Optional[str]) -> bool:
    return (remote_jid or "").lower().endswith("@g.us")


def is_lid(jid: Optional[str]) -> bool:
    return "@lid" in (jid or "").lower()

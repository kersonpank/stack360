"""Normalização determinística de identidades e entidades. SEM fuzzy.

Identidades fortes globais no v1: SOMENTE ``email`` e ``phone``.
``whatsapp`` numérico que resolve a E.164 -> vira ``phone``.
``instagram`` / ``linkedin`` / ``visitor_id`` / ``external_id`` /
``legacy_contact_id`` / ``whatsapp`` JID -> source-scoped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.stack360.security.hashing import value_hash

STRONG_GLOBAL_TYPES = ("email", "phone")
_LOCAL_TYPES = ("visitor_id", "external_id", "legacy_contact_id")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

try:  # pragma: no cover - opcional
    import phonenumbers

    _HAVE_PHONENUMBERS = True
except Exception:  # pragma: no cover
    phonenumbers = None  # type: ignore
    _HAVE_PHONENUMBERS = False


@dataclass(frozen=True)
class NormalizedIdentity:
    identity_type: str          # tipo final (pode diferir do de entrada: whatsapp->phone)
    value_normalized: str
    value_hash: str
    is_strong_global: bool
    source_scoped: bool         # True => precisa de data_source_id


def normalize_email(raw: str) -> Optional[str]:
    v = (raw or "").strip().lower()
    return v if _EMAIL_RE.match(v) else None


def normalize_phone_e164(raw: str, region: str = "BR") -> Optional[str]:
    if raw is None:
        return None
    s = raw.strip()
    digits = re.sub(r"[^\d+]", "", s)
    if _HAVE_PHONENUMBERS:
        try:
            num = phonenumbers.parse(s if s.startswith("+") else digits, None if s.startswith("+") else region)
            if phonenumbers.is_valid_number(num):
                return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            pass
        return None
    # Fallback mínimo BR (menos preciso — documentado)
    d = re.sub(r"\D", "", digits)
    if s.startswith("+") and 8 <= len(d) <= 15:
        return "+" + d
    if len(d) in (10, 11):  # DDD + numero, assume BR
        return "+55" + d
    if len(d) in (12, 13) and d.startswith("55"):
        return "+" + d
    return None


def normalize_domain(raw: str) -> Optional[str]:
    if not raw:
        return None
    v = raw.strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = v.split("/")[0].split("?")[0]
    v = re.sub(r"^www\.", "", v)
    return v or None


_CNPJ_RE = re.compile(r"\d")


def normalize_cnpj(raw: str) -> Optional[str]:
    if not raw:
        return None
    d = "".join(_CNPJ_RE.findall(raw))
    return d if len(d) == 14 else None


_LEGAL_SUFFIX_RE = re.compile(
    r"\b(ltda|epp|eireli|me|s\.?\s?a\.?|sa|s/a|mei)\.?\s*$", re.IGNORECASE
)


def normalize_company_name(raw: str) -> Optional[str]:
    if not raw:
        return None
    v = raw.strip().lower()
    v = _LEGAL_SUFFIX_RE.sub("", v).strip()
    v = re.sub(r"[^\w\s&.-]", "", v)
    v = re.sub(r"\s+", " ", v).strip()
    return v or None


def _handle(raw: str) -> Optional[str]:
    if not raw:
        return None
    v = raw.strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = v.split("?")[0].rstrip("/")
    v = v.lstrip("@")
    return v or None


def normalize_identity(identity_type: str, value: str, has_data_source: bool) -> Optional[NormalizedIdentity]:
    """Retorna None se o valor for inválido/impossível de normalizar."""
    t = (identity_type or "").strip().lower()

    if t == "email":
        n = normalize_email(value)
        if not n:
            return None
        return NormalizedIdentity("email", n, value_hash("email", n), True, False)

    if t == "phone":
        n = normalize_phone_e164(value)
        if not n:
            return None
        return NormalizedIdentity("phone", n, value_hash("phone", n), True, False)

    if t == "whatsapp":
        # numérico que resolve a E.164 -> tratado como phone (forte global)
        n = normalize_phone_e164(value)
        if n:
            return NormalizedIdentity("phone", n, value_hash("phone", n), True, False)
        # JID / não-numérico -> source-scoped
        jid = (value or "").strip().lower()
        if not jid:
            return None
        return NormalizedIdentity("whatsapp", jid, value_hash("whatsapp", jid), False, True)

    if t in ("instagram", "linkedin"):
        n = _handle(value)
        if not n:
            return None
        return NormalizedIdentity(t, n, value_hash(t, n), False, True)

    if t in _LOCAL_TYPES:
        n = (value or "").strip()
        if not n:
            return None
        return NormalizedIdentity(t, n, value_hash(t, n), False, True)

    # tipo desconhecido -> tratado como source-scoped genérico
    n = (value or "").strip()
    if not n:
        return None
    return NormalizedIdentity(t or "unknown", n, value_hash(t or "unknown", n), False, True)

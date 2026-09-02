from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any

_API_KEY_PREFIX = "st_"
_PREFIX_LEN = 12  # "st_" + 9 chars — só p/ exibição/admin (NÃO é chave única)


def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)


def payload_hash(payload: Any) -> str:
    return sha256_hex(canonical_json(payload))


def value_hash(namespace: str, normalized_value: str) -> str:
    """Hash canônico de uma identidade / observação: ``sha256("<ns>:<value>")``."""
    return sha256_hex(f"{namespace}:{normalized_value}")


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def generate_api_key() -> tuple[str, str, str]:
    """Retorna (plaintext, key_prefix, key_hash). Plaintext NUNCA persistida."""
    plaintext = _API_KEY_PREFIX + secrets.token_urlsafe(32)
    return plaintext, plaintext[:_PREFIX_LEN], sha256_hex(plaintext)


def api_key_prefix(plaintext: str) -> str:
    return plaintext[:_PREFIX_LEN]


def hmac_sha256_hex(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()

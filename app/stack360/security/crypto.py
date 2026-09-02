"""Cifra o webhook secret at-rest (AES-GCM).

Master key: env ``STACK360_WEBHOOK_SECRET_KEY`` (base64 url-safe, 32 bytes).
Ausente OU ``cryptography`` indisponível => HMAC configurável NÃO é suportado
(fallback: webhook autentica só por API key source-bound). Nunca plaintext,
nunca hash irreversível para "validar" HMAC.
"""
from __future__ import annotations

import base64
import os
from typing import Optional

_KEY_ID = "env:STACK360_WEBHOOK_SECRET_KEY"

try:  # pragma: no cover - depende do ambiente
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _HAVE_CRYPTO = True
except Exception:  # pragma: no cover
    AESGCM = None  # type: ignore
    _HAVE_CRYPTO = False


def _master_key() -> Optional[bytes]:
    raw = os.environ.get("STACK360_WEBHOOK_SECRET_KEY")
    if not raw:
        return None
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except Exception:
        key = raw.encode("utf-8")
    if len(key) not in (16, 24, 32):
        key = key.ljust(32, b"\0")[:32]
    return key


def hmac_available() -> bool:
    return _HAVE_CRYPTO and _master_key() is not None


def encrypt_secret(plaintext: str) -> tuple[bytes, str]:
    if not hmac_available():
        raise RuntimeError("webhook HMAC not available (no cryptography or master key)")
    key = _master_key()
    assert key is not None
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)  # type: ignore
    return nonce + ct, _KEY_ID


def decrypt_secret(blob: bytes) -> str:
    if not hmac_available():
        raise RuntimeError("webhook HMAC not available")
    key = _master_key()
    assert key is not None
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")  # type: ignore

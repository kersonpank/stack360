"""Configuração do Stack360 — independente do ``app.core.config`` legado.

Todos os campos têm prefixo ``STACK360_`` no ambiente, então ler o ``.env``
legado é inócuo (nenhuma chave colide).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Stack360Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STACK360_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Banco LOCAL do core novo (dev). Testes usam STACK360_TEST_DATABASE_URL.
    database_url: str = "postgresql+psycopg2://stack360:stack360@localhost:5433/stack360_dev"
    test_database_url: str = "postgresql+psycopg2://stack360:stack360@localhost:5433/stack360_test"

    # Ingestão em lote
    batch_max: int = 100
    max_payload_bytes: int = 1_000_000

    # Rate limit (best-effort, em memória, por api_key.id)
    rate_limit_per_min: int = 600

    # Master key p/ cifrar webhook secret at-rest (AES-GCM). Ausente => HMAC
    # configurável não é implementado (fallback: só API key source-bound).
    webhook_secret_key: Optional[str] = None

    # Context endpoints: cap default por seção
    context_section_limit: int = 20
    read_page_default: int = 50
    read_page_max: int = 200

    # CORS: origens EXTRA autorizadas no navegador (CSV). localhost:3000-3005
    # já é sempre permitido para dev. Em produção: domínio do frontend.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        base = [f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in range(3000, 3006)]
        extra = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return base + extra


@lru_cache
def get_settings() -> Stack360Settings:
    return Stack360Settings()

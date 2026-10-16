"""Fontes cadastradas por configuração — dict Python simples, não um sistema
de plugin. Um reader pode cobrir várias instâncias/contas ao mesmo tempo (é
o caso do WhatsApp hoje: 1 tabela, 4 `source_account`) — o `source_key` de
cada envelope é resolvido dinamicamente a partir do próprio dado, não fixado
aqui. Uma fonte real valida esse nível de abstração; a segunda fonte real
decide se precisa de mais.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from sqlalchemy.engine import Engine

from app.stack360.projection.envelope import SourceEnvelope
from app.stack360.projection.readers import whatsapp_legacy
from app.stack360.projection.readers.base import readonly_engine

ReaderFn = Callable[..., Iterator[SourceEnvelope]]


@dataclass(frozen=True)
class ReaderConfig:
    name: str               # só identificação/log
    source_type: str         # usado na auto-criação de DataSource
    reader: ReaderFn          # iter_envelopes(engine, since_cursor=..., ...)
    database_url_env: str      # qual env var dá a connection string desta fonte


READERS: list[ReaderConfig] = [
    ReaderConfig(
        name="whatsapp-legacy",
        source_type="whatsapp-legacy",
        reader=whatsapp_legacy.iter_envelopes,
        # NÃO usar "DATABASE_URL" aqui — no container `api` do Stack360 essa
        # variável já foi repropositada pro Postgres do PRÓPRIO Stack360
        # (compat com Alembic/config legado), não pro banco legado do
        # WhatsApp. Precisa de uma env var própria, sem ambiguidade.
        database_url_env="LEGACY_WHATSAPP_DATABASE_URL",
    ),
]


def build_engine(reader_config: ReaderConfig, env: dict) -> Engine:
    url = env.get(reader_config.database_url_env)
    if not url:
        raise RuntimeError(f"env var {reader_config.database_url_env} ausente pra reader {reader_config.name}")
    return readonly_engine(url)

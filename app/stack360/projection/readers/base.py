"""Base comum a todo reader — conexão somente leitura, sessão curta."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def readonly_engine(database_url: str) -> Engine:
    """Engine com `default_transaction_read_only=on` — nunca escreve na
    origem, mesmo que o usuário do banco ainda tenha permissão de escrita.
    Sessões são sempre curtas (abrir/ler/fechar), nunca ficam "idle in
    transaction" (incidente conhecido do app legado)."""
    return create_engine(
        database_url,
        connect_args={"options": "-c default_transaction_read_only=on"},
        pool_pre_ping=True,
    )

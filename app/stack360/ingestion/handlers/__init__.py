"""Registry de handlers por família de ``event_type``.

Novos tipos = novo handler em código, ZERO migration. Resolução: tipo exato
-> senão fallback pelo prefixo ``family.*``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.stack360.auth import AuthContext
from app.stack360.models.ingestion_event import IngestionEvent
from app.stack360.schemas.envelope import StackEvent


@dataclass
class HandlerContext:
    db: Session
    auth: AuthContext
    event: StackEvent
    ingestion_event: IngestionEvent
    # entidades tocadas (retornadas na resposta)
    entities: dict[str, Any] = field(default_factory=dict)
    # resolution_cases informativos (ambiguidade) — criados no commit de sucesso
    pending_cases: list[dict] = field(default_factory=list)

    @property
    def workspace_id(self) -> uuid.UUID:
        return self.auth.workspace_id

    @property
    def data_source_id(self) -> uuid.UUID:
        assert self.auth.data_source_id is not None
        return self.auth.data_source_id


Handler = Callable[[HandlerContext], None]

_EXACT: dict[str, Handler] = {}
_FAMILY: dict[str, Handler] = {}


def register(*, exact: Optional[str] = None, family: Optional[str] = None) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        if exact:
            _EXACT[exact] = fn
        if family:
            _FAMILY[family] = fn
        return fn

    return deco


def get_handler(event_type: str) -> Optional[Handler]:
    if event_type in _EXACT:
        return _EXACT[event_type]
    fam = event_type.split(".", 1)[0]
    return _FAMILY.get(fam)


def load_handlers() -> None:
    """Importa os módulos de família para popular o registry."""
    from app.stack360.ingestion.handlers import (  # noqa: F401
        company as _c,
        experience as _e,
        identity as _i,
        interaction as _int,
        observation as _o,
        score as _s,
    )

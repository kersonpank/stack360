"""Registry de extractors por `envelope_type` — mesmo padrão de
`app/stack360/ingestion/handlers/__init__.py` (registry por tipo), reaplicado
aqui. Novo tipo de envelope = novo extractor em código, zero migration."""
from __future__ import annotations

from typing import Callable, Optional

from app.stack360.projection.envelope import SourceEnvelope
from app.stack360.schemas.envelope import StackEvent

Extractor = Callable[[SourceEnvelope], list[StackEvent]]

_REGISTRY: dict[str, Extractor] = {}


def register(envelope_type: str) -> Callable[[Extractor], Extractor]:
    def deco(fn: Extractor) -> Extractor:
        _REGISTRY[envelope_type] = fn
        return fn

    return deco


def extractor_for(envelope_type: str) -> Optional[Extractor]:
    return _REGISTRY.get(envelope_type)


def load_extractors() -> None:
    """Importa os módulos de extractor pra popular o registry."""
    from app.stack360.projection.extractors import whatsapp_message as _wa  # noqa: F401

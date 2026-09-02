"""Registry de adapters de webhook inbound, por ``data_sources.source_type``.

V1 só tem ``passthrough``. Integração futura (Gmail, Instagram, WhatsApp, ...)
registra o próprio adapter aqui — SEM tocar no canonical core.

    raw webhook  ->  adapter  ->  StackEvent (universal)  ->  gateway
"""
from __future__ import annotations

from typing import Callable

from app.stack360.schemas.envelope import StackEvent

Adapter = Callable[[bytes, dict, str], StackEvent]

_REGISTRY: dict[str, Adapter] = {}


def register_adapter(source_type: str, fn: Adapter) -> None:
    _REGISTRY[source_type] = fn


def get_adapter(source_type: str) -> Adapter:
    from adapters.passthrough import passthrough_adapter

    return _REGISTRY.get(source_type, passthrough_adapter)

"""Contrato universal de evento (envelope). Sem regras específicas de
diagnóstico aqui — ``data`` é validado por família no handler.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

SUPPORTED_MAJOR = {1}


def schema_major_supported(schema_version: str) -> bool:
    try:
        return int(str(schema_version).split(".")[0]) in SUPPORTED_MAJOR
    except Exception:
        return False


class IdentityIn(BaseModel):
    type: str
    value: str
    verified: bool = False
    confidence: Optional[float] = None


class SubjectIn(BaseModel):
    identities: list[IdentityIn] = Field(default_factory=list)


class CompanyIn(BaseModel):
    cnpj: Optional[str] = None
    domain: Optional[str] = None
    name: Optional[str] = None
    external_id: Optional[str] = None

    def is_empty(self) -> bool:
        return not any([self.cnpj, self.domain, self.name, self.external_id])


class ContextIn(BaseModel):
    visitor_id: Optional[str] = None
    experience_key: Optional[str] = None
    experience_version: Optional[str] = None
    external_run_id: Optional[str] = None
    channel: Optional[str] = None
    direction: Optional[str] = None
    model_config = {"extra": "allow"}


class AttributionIn(BaseModel):
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    referrer: Optional[str] = None
    landing_url: Optional[str] = None
    model_config = {"extra": "allow"}


class StackEvent(BaseModel):
    schema_version: str
    event_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    occurred_at: datetime
    subject: Optional[SubjectIn] = None
    company: Optional[CompanyIn] = None
    data: dict[str, Any] = Field(default_factory=dict)
    context: Optional[ContextIn] = None
    attribution: Optional[AttributionIn] = None

    @property
    def family(self) -> str:
        return self.event_type.split(".", 1)[0]


class BatchIn(BaseModel):
    events: list[StackEvent]

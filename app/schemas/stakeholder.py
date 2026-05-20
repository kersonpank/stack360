from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class StakeholderSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact_id: str
    telefone: Optional[str] = None
    nome_atual: Optional[str] = None
    tipo_relacionamento: Optional[str] = None
    status_relacionamento: Optional[str] = None
    ultimo_contato_em: Optional[datetime] = None
    total_mensagens: Optional[int] = None
    score_oportunidade: Optional[float] = None
    score_risco: Optional[float] = None
    tags: Optional[List[str]] = None


class StakeholderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[StakeholderSearchResult]


class StakeholderDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact_id: str
    telefone: Optional[str] = None
    nome_atual: Optional[str] = None
    tipo_relacionamento: Optional[str] = None
    status_relacionamento: Optional[str] = None
    primeiro_contato_em: Optional[datetime] = None
    ultimo_contato_em: Optional[datetime] = None
    total_mensagens: Optional[int] = None
    score_oportunidade: Optional[float] = None
    score_risco: Optional[float] = None
    tags: Optional[List[str]] = None
    resumo_geral: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

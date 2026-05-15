from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: int  # bigint no banco
    contact_id: Optional[str] = None
    conversation_id: Optional[str] = None
    origem_message_id: Optional[str] = None
    tipo_oportunidade: Optional[str] = None
    descricao: Optional[str] = None
    score: Optional[float] = None
    status: Optional[str] = None
    proxima_acao: Optional[str] = None
    responsavel: Optional[str] = None
    espo_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

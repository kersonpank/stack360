from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    data_hora: Optional[datetime] = None
    enviada_por_mim: Optional[bool] = None
    nome_contato: Optional[str] = None
    tipo_mensagem: Optional[str] = None
    texto: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None


class MessageList(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[MessageResponse]

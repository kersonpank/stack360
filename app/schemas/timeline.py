from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    contact_id: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    data_hora: Optional[datetime] = None
    tipo_evento: Optional[str] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    importancia: Optional[str] = None
    payload: Optional[Any] = None

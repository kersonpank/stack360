from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str
    contact_id: Optional[str] = None
    source_account_id: Optional[str] = None
    instance_name: Optional[str] = None
    remote_jid: Optional[str] = None
    tipo_chat: Optional[str] = None
    primeira_mensagem_em: Optional[datetime] = None
    ultima_mensagem_em: Optional[datetime] = None
    total_mensagens: Optional[int] = None
    assunto_principal: Optional[str] = None
    resumo_conversa: Optional[str] = None
    status_conversa: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    evidence_id: int
    contact_id: str
    conversation_id: Optional[str]
    message_id: Optional[str]
    evidence_type: str
    evidence_value: str
    confidence: Optional[Decimal]
    source: Optional[str]
    payload: Optional[Dict[str, Any]]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}

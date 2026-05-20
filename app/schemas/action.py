from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ActionResponse(BaseModel):
    action_id: int
    contact_id: str
    stakeholder_name: Optional[str] = None
    conversation_id: Optional[str] = None
    opportunity_id: Optional[int] = None
    action_type: str
    title: str
    description: Optional[str] = None
    priority_score: Optional[Decimal] = None
    reason: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    due_at: Optional[datetime] = None
    source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActionSummaryResponse(BaseModel):
    total_actions: int
    novas: int
    em_andamento: int
    concluidas: int
    descartadas: int
    by_action_type: Dict[str, int]
    top_priority: List[ActionResponse]


class ActionStatusPatch(BaseModel):
    status: str


class ActionStatusResponse(BaseModel):
    total_actions: int
    pending_actions: int
    actions_by_type: Dict[str, int]
    actions_by_status: Dict[str, int]
    last_generated_at: Optional[datetime] = None

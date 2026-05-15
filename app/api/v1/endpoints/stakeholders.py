from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.contact_repository import ContactRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.timeline_repository import TimelineRepository
from app.schemas.conversation import ConversationResponse
from app.schemas.opportunity import OpportunityResponse
from app.schemas.stakeholder import StakeholderDetail, StakeholderSearchResult
from app.schemas.timeline import TimelineEventResponse
from app.services.conversation_service import StakeholderConversationService
from app.services.opportunity_service import OpportunityService
from app.services.stakeholder_service import StakeholderService
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/stakeholders")


@router.get("/search", response_model=List[StakeholderSearchResult])
def search_stakeholders(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    return StakeholderService(ContactRepository(db)).search_stakeholders(q)


@router.get("/{contact_id}", response_model=StakeholderDetail)
def get_stakeholder(contact_id: str, db: Session = Depends(get_db)):
    return StakeholderService(ContactRepository(db)).get_stakeholder(contact_id)


@router.get("/{contact_id}/conversations", response_model=List[ConversationResponse])
def get_stakeholder_conversations(contact_id: str, db: Session = Depends(get_db)):
    return StakeholderConversationService(ConversationRepository(db)).get_conversations(contact_id)


@router.get("/{contact_id}/timeline", response_model=List[TimelineEventResponse])
def get_stakeholder_timeline(contact_id: str, db: Session = Depends(get_db)):
    return TimelineService(TimelineRepository(db)).get_timeline(contact_id)


@router.get("/{contact_id}/opportunities", response_model=List[OpportunityResponse])
def get_stakeholder_opportunities(contact_id: str, db: Session = Depends(get_db)):
    return OpportunityService(OpportunityRepository(db)).get_opportunities(contact_id)

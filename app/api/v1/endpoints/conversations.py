from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.message_repository import MessageRepository
from app.schemas.message import MessageList
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations")


@router.get("/{conversation_id}/messages", response_model=MessageList)
def get_messages(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    return ConversationService(MessageRepository(db)).get_messages(
        conversation_id, limit=limit, offset=offset, order=order
    )

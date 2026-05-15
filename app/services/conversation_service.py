from typing import List

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.conversation import ConversationResponse
from app.schemas.message import MessageList, MessageResponse


class ConversationService:
    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    def get_messages(
        self,
        conversation_id: str,
        limit: int,
        offset: int,
        order: str,
    ) -> MessageList:
        items, total = self.message_repo.get_by_conversation_id(
            conversation_id, limit=limit, offset=offset, order=order
        )
        return MessageList(
            total=total,
            limit=limit,
            offset=offset,
            items=[MessageResponse.model_validate(m) for m in items],
        )


class StakeholderConversationService:
    def __init__(self, conv_repo: ConversationRepository):
        self.conv_repo = conv_repo

    def get_conversations(self, contact_id: str) -> List[ConversationResponse]:
        rows = self.conv_repo.get_by_contact_id(contact_id)
        return [ConversationResponse.model_validate(row) for row in rows]

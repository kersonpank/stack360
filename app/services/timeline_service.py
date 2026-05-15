from typing import List

from app.repositories.timeline_repository import TimelineRepository
from app.schemas.timeline import TimelineEventResponse


class TimelineService:
    def __init__(self, repo: TimelineRepository):
        self.repo = repo

    def get_timeline(self, contact_id: str) -> List[TimelineEventResponse]:
        events = self.repo.get_by_contact_id(contact_id)
        return [TimelineEventResponse.model_validate(e) for e in events]

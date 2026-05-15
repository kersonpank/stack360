from typing import List

from app.repositories.opportunity_repository import OpportunityRepository
from app.schemas.opportunity import OpportunityResponse


class OpportunityService:
    def __init__(self, repo: OpportunityRepository):
        self.repo = repo

    def get_opportunities(self, contact_id: str) -> List[OpportunityResponse]:
        opps = self.repo.get_by_contact_id(contact_id)
        return [OpportunityResponse.model_validate(o) for o in opps]

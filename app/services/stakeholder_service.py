from typing import List

from fastapi import HTTPException

from app.repositories.contact_repository import ContactRepository
from app.schemas.stakeholder import StakeholderDetail, StakeholderSearchResult


class StakeholderService:
    def __init__(self, repo: ContactRepository):
        self.repo = repo

    def search_stakeholders(self, q: str) -> List[StakeholderSearchResult]:
        contacts = self.repo.search(q)
        return [StakeholderSearchResult.model_validate(c) for c in contacts]

    def get_stakeholder(self, contact_id: str) -> StakeholderDetail:
        contact = self.repo.get_by_id(contact_id)
        if contact is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stakeholder '{contact_id}' não encontrado",
            )
        return StakeholderDetail.model_validate(contact)

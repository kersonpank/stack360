from typing import List, Optional

from fastapi import HTTPException

from app.repositories.contact_repository import ContactRepository
from app.schemas.stakeholder import (
    StakeholderDetail,
    StakeholderListResponse,
    StakeholderSearchResult,
)


class StakeholderService:
    def __init__(self, repo: ContactRepository):
        self.repo = repo

    def search_stakeholders(self, q: str) -> List[StakeholderSearchResult]:
        contacts = self.repo.search(q)
        return [StakeholderSearchResult.model_validate(c) for c in contacts]

    def list_stakeholders(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        q: Optional[str] = None,
        relationship_type: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        sort: str = "last_interaction",
        order: str = "desc",
    ) -> StakeholderListResponse:
        contacts, total = self.repo.list(
            page=page,
            page_size=page_size,
            q=q,
            relationship_type=relationship_type,
            status=status,
            tag=tag,
            sort=sort,
            order=order,
        )
        return StakeholderListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[StakeholderSearchResult.model_validate(c) for c in contacts],
        )

    def get_stakeholder(self, contact_id: str) -> StakeholderDetail:
        contact = self.repo.get_by_id(contact_id)
        if contact is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stakeholder '{contact_id}' não encontrado",
            )
        return StakeholderDetail.model_validate(contact)

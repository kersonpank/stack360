from sqlalchemy.orm import Session

from app.repositories.system_repository import SystemRepository
from app.schemas.system import NormalizationStatusResponse


class SystemService:
    def __init__(self, db: Session):
        self.repo = SystemRepository(db)

    def get_normalization_status(self) -> NormalizationStatusResponse:
        data = self.repo.get_normalization_status()
        return NormalizationStatusResponse(**data)

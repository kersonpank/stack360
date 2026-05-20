# TODO: add auth before exposing to production
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.action_repository import ActionRepository
from app.schemas.action import ActionResponse, ActionStatusPatch, ActionSummaryResponse

router = APIRouter(prefix="/actions", tags=["actions"])


def _repo(db: Session = Depends(get_db)) -> ActionRepository:
    return ActionRepository(read_db=db, write_db=db)


@router.get("", response_model=List[ActionResponse])
def list_actions(
    status: Optional[str] = None,
    action_type: Optional[str] = None,
    min_priority: Optional[float] = None,
    contact_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    repo: ActionRepository = Depends(_repo),
):
    rows = repo.get_actions(
        status=status,
        action_type=action_type,
        min_priority=min_priority,
        contact_id=contact_id,
        limit=limit,
        offset=offset,
    )
    return [ActionResponse(**r) for r in rows]


@router.get("/summary", response_model=ActionSummaryResponse)
def actions_summary(repo: ActionRepository = Depends(_repo)):
    data = repo.get_summary()
    data["top_priority"] = [ActionResponse(**r) for r in data["top_priority"]]
    return ActionSummaryResponse(**data)


@router.patch("/{action_id}/status", response_model=ActionResponse)
def patch_action_status(
    action_id: int,
    body: ActionStatusPatch,
    db: Session = Depends(get_db),
):
    valid_statuses = {"nova", "em_andamento", "concluida", "descartada"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status deve ser um de: {sorted(valid_statuses)}")
    repo = ActionRepository(read_db=db, write_db=db)
    action = repo.update_status(action_id, body.status)
    if not action:
        raise HTTPException(status_code=404, detail="Action não encontrada")
    db.commit()
    db.refresh(action)
    return ActionResponse.model_validate(action)

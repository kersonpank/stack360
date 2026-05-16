from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.scheduler.scheduler_state import scheduler_state
from app.schemas.system import NormalizationStatusResponse, SchedulerStatusResponse
from app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/normalization-status", response_model=NormalizationStatusResponse)
def normalization_status(db: Session = Depends(get_db)):
    return SystemService(db).get_normalization_status()


@router.get("/normalizer-scheduler-status", response_model=SchedulerStatusResponse)
def normalizer_scheduler_status():
    return SchedulerStatusResponse(
        enabled=scheduler_state.enabled,
        running=scheduler_state.running,
        interval_seconds=settings.normalizer_interval_seconds,
        nightly_enabled=settings.normalizer_nightly_enabled,
        nightly_hour=settings.normalizer_nightly_hour,
        last_run_started_at=scheduler_state.last_run_started_at,
        last_run_finished_at=scheduler_state.last_run_finished_at,
        last_success_at=scheduler_state.last_success_at,
        last_error_at=scheduler_state.last_error_at,
        last_error_message=scheduler_state.last_error_message,
        last_result=scheduler_state.last_result,
        total_runs=scheduler_state.total_runs,
        total_success=scheduler_state.total_success,
        total_failures=scheduler_state.total_failures,
        total_skipped_by_lock=scheduler_state.total_skipped_by_lock,
        next_run_estimate=scheduler_state.next_run_estimate,
    )

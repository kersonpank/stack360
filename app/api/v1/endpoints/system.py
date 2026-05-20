from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.scheduler.enrichment_scheduler_state import enrichment_scheduler_state
from app.scheduler.scheduler_state import scheduler_state
from app.schemas.system import (
    EnrichmentSchedulerStatusResponse,
    EnrichmentStatusResponse,
    NormalizationStatusResponse,
    SchedulerStatusResponse,
)
from app.services.system_service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/enrichment-status", response_model=EnrichmentStatusResponse)
def enrichment_status(db: Session = Depends(get_db)):
    from app.repositories.enrichment_repository import EnrichmentRepository
    counts = EnrichmentRepository(read_db=db, write_db=db).get_enrichment_counts()
    return EnrichmentStatusResponse(**counts)


@router.get("/normalization-status", response_model=NormalizationStatusResponse)
def normalization_status(db: Session = Depends(get_db)):
    return SystemService(db).get_normalization_status()


@router.get("/enrichment-scheduler-status", response_model=EnrichmentSchedulerStatusResponse)
def enrichment_scheduler_status():
    return EnrichmentSchedulerStatusResponse(
        enabled=enrichment_scheduler_state.enabled,
        running=enrichment_scheduler_state.running,
        interval_seconds=settings.enrichment_interval_seconds,
        nightly_enabled=settings.enrichment_nightly_enabled,
        nightly_hour=settings.enrichment_nightly_hour,
        use_llm=settings.enrichment_use_llm,
        last_run_started_at=enrichment_scheduler_state.last_run_started_at,
        last_run_finished_at=enrichment_scheduler_state.last_run_finished_at,
        last_success_at=enrichment_scheduler_state.last_success_at,
        last_error_at=enrichment_scheduler_state.last_error_at,
        last_error_message=enrichment_scheduler_state.last_error_message,
        last_result=enrichment_scheduler_state.last_result,
        total_runs=enrichment_scheduler_state.total_runs,
        total_success=enrichment_scheduler_state.total_success,
        total_failures=enrichment_scheduler_state.total_failures,
        total_skipped_by_lock=enrichment_scheduler_state.total_skipped_by_lock,
        next_run_estimate=enrichment_scheduler_state.next_run_estimate,
    )


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

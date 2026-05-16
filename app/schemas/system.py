from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SourceAccountStatus(BaseModel):
    source_account_id: Optional[str]
    instance_name: Optional[str]
    total_raw: int
    normalized: int
    pending: int


class NormalizationStatusResponse(BaseModel):
    total_raw: int
    total_raw_normalized: int
    total_raw_pending: int
    total_contacts: int
    total_conversations: int
    total_messages: int
    by_source_account: List[SourceAccountStatus]


class SchedulerStatusResponse(BaseModel):
    enabled: bool
    running: bool
    interval_seconds: int
    nightly_enabled: bool
    nightly_hour: int
    last_run_started_at: Optional[datetime]
    last_run_finished_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_error_at: Optional[datetime]
    last_error_message: Optional[str]
    last_result: Optional[Dict[str, Any]]
    total_runs: int
    total_success: int
    total_failures: int
    total_skipped_by_lock: int
    next_run_estimate: Optional[datetime]

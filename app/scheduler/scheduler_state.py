from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


@dataclass
class SchedulerState:
    enabled: bool = False
    running: bool = False
    last_run_started_at: Optional[datetime] = None
    last_run_finished_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    last_result: Optional[dict] = None
    total_runs: int = 0
    total_success: int = 0
    total_failures: int = 0
    total_skipped_by_lock: int = 0
    next_run_estimate: Optional[datetime] = None
    last_nightly_date: Optional[date] = None


scheduler_state = SchedulerState()

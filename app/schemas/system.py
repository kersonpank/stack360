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


class TagCount(BaseModel):
    tag: str
    count: int


class EnrichmentStatusResponse(BaseModel):
    total_contacts: int
    contacts_enriched: int
    contacts_pending: int
    total_evidence: int
    total_timeline_events: int
    total_opportunities: int
    opportunities_open: int
    last_enriched_at: Optional[datetime]
    by_tipo_relacionamento: Dict[str, int]
    top_tags: List[TagCount]


class EnrichmentSchedulerStatusResponse(BaseModel):
    enabled: bool
    running: bool
    interval_seconds: int
    nightly_enabled: bool
    nightly_hour: int
    use_llm: bool
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

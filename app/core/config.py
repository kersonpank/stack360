from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    api_env: str = "development"
    normalizer_database_url: Optional[str] = None

    # Scheduler
    normalizer_scheduler_enabled: bool = False
    normalizer_interval_seconds: int = 300
    normalizer_incremental_limit: int = 1000
    normalizer_incremental_max_batches: int = 1
    normalizer_nightly_enabled: bool = True
    normalizer_nightly_hour: int = 2
    normalizer_nightly_limit: int = 5000
    normalizer_nightly_max_batches: int = 5

    # Enrichment Scheduler (disabled by default)
    enrichment_scheduler_enabled: bool = False
    enrichment_interval_seconds: int = 900
    enrichment_incremental_limit: int = 100
    enrichment_incremental_max_batches: int = 1
    enrichment_nightly_enabled: bool = True
    enrichment_nightly_hour: int = 3
    enrichment_nightly_limit: int = 1000
    enrichment_nightly_max_batches: int = 3
    enrichment_use_llm: bool = False

    # LLM enrichment (disabled by default)
    llm_enabled: bool = False
    llm_provider: str = "openrouter"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model_extractor: Optional[str] = None
    llm_model_summarizer: Optional[str] = None
    llm_model_strong: Optional[str] = None
    llm_daily_budget_usd: float = 10.0
    llm_timeout_seconds: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

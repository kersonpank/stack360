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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

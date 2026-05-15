from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    api_env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

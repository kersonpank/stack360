import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost:5432/testdb")
os.environ.setdefault("API_ENV", "testing")
# Force scheduler off in tests regardless of .env — env vars take precedence over .env in pydantic-settings
os.environ["NORMALIZER_SCHEDULER_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db


def override_get_db():
    yield MagicMock(spec=Session)


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

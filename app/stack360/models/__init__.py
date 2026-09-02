"""Todos os 21 models do Stack360 (schema ``stack360``).

Importar este módulo popula ``Stack360Base.metadata`` (usado por
``create_all`` nos testes). A migration manual é a fonte de verdade em prod.
"""
from app.stack360.models.api_key import ApiKey
from app.stack360.models.company import (
    Company,
    PersonCompanyRelationship,
    WorkspaceCompany,
)
from app.stack360.models.data_source import DataSource, SourceSyncState
from app.stack360.models.experience import Answer, Experience, ExperienceRun, Result
from app.stack360.models.ingestion_event import IngestionEvent
from app.stack360.models.interaction import Interaction
from app.stack360.models.observation import Observation
from app.stack360.models.person import Person, PersonIdentity, WorkspacePerson
from app.stack360.models.resolution import ResolutionCase, ResolutionRecommendation
from app.stack360.models.score import ScoreHistory
from app.stack360.models.webhook import WebhookEndpoint
from app.stack360.models.workspace import Workspace

ALL_MODELS = [
    Workspace,
    DataSource,
    ApiKey,
    Person,
    PersonIdentity,
    WorkspacePerson,
    Company,
    WorkspaceCompany,
    PersonCompanyRelationship,
    IngestionEvent,
    Interaction,
    Observation,
    Experience,
    ExperienceRun,
    Answer,
    Result,
    ScoreHistory,
    SourceSyncState,
    WebhookEndpoint,
    ResolutionCase,
    ResolutionRecommendation,
]

TABLE_NAMES = sorted(m.__tablename__ for m in ALL_MODELS)

__all__ = [m.__name__ for m in ALL_MODELS] + ["ALL_MODELS", "TABLE_NAMES"]

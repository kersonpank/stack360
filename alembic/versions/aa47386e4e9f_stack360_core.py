"""stack360 integration core — canonical schema (21 tables)

Revision ID: aa47386e4e9f
Revises: 13b31f818410
Create Date: 2026-09-01

MANUAL, ADITIVA. Cria SOMENTE o schema ``stack360`` e suas tabelas.
NAO toca em ``public`` (legado). NAO roda ``CREATE EXTENSION`` (UUID e gerado
pela aplicacao). Nunca gerada por autogenerate.

Bootstrap em banco local vazio (NAO usar ``alembic upgrade head`` — a cadeia
legada nao sobe em DB vazio):
    alembic stamp 13b31f818410
    alembic upgrade aa47386e4e9f
"""
from alembic import op

revision = "aa47386e4e9f"
down_revision = "13b31f818410"
branch_labels = None
depends_on = None

STACK360_DDL = r"""
CREATE TABLE stack360.companies (
	id UUID NOT NULL, 
	canonical_name VARCHAR, 
	normalized_name VARCHAR, 
	domain VARCHAR, 
	cnpj_normalized VARCHAR, 
	website VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_companies PRIMARY KEY (id)
);

CREATE INDEX ix_companies_domain ON stack360.companies (domain);

CREATE INDEX ix_companies_normalized_name ON stack360.companies (normalized_name);

CREATE UNIQUE INDEX uq_companies_cnpj_normalized ON stack360.companies (cnpj_normalized) WHERE cnpj_normalized IS NOT NULL;

CREATE TABLE stack360.people (
	id UUID NOT NULL, 
	canonical_name VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_people PRIMARY KEY (id)
);

CREATE TABLE stack360.workspaces (
	id UUID NOT NULL, 
	slug VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_workspaces PRIMARY KEY (id), 
	CONSTRAINT uq_workspaces_slug UNIQUE (slug)
);

CREATE TABLE stack360.data_sources (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	key VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	source_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	metadata JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_data_sources PRIMARY KEY (id), 
	CONSTRAINT uq_data_sources_workspace_id_key UNIQUE (workspace_id, key), 
	CONSTRAINT fk_data_sources_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id)
);

CREATE INDEX ix_stack360_data_sources_workspace_id ON stack360.data_sources (workspace_id);

CREATE TABLE stack360.experiences (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	key VARCHAR NOT NULL, 
	version VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	experience_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	metadata JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_experiences PRIMARY KEY (id), 
	CONSTRAINT uq_experiences_ws_key_version UNIQUE (workspace_id, key, version), 
	CONSTRAINT fk_experiences_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id)
);

CREATE TABLE stack360.workspace_companies (
	workspace_id UUID NOT NULL, 
	company_id UUID NOT NULL, 
	status VARCHAR NOT NULL, 
	first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_workspace_companies PRIMARY KEY (workspace_id, company_id), 
	CONSTRAINT fk_workspace_companies_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_workspace_companies_company_id_companies FOREIGN KEY(company_id) REFERENCES stack360.companies (id)
);

CREATE TABLE stack360.workspace_people (
	workspace_id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	status VARCHAR NOT NULL, 
	first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_workspace_people PRIMARY KEY (workspace_id, person_id), 
	CONSTRAINT fk_workspace_people_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_workspace_people_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id)
);

CREATE TABLE stack360.api_keys (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	data_source_id UUID, 
	name VARCHAR NOT NULL, 
	key_prefix VARCHAR NOT NULL, 
	key_hash VARCHAR NOT NULL, 
	scopes VARCHAR[] NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_api_keys PRIMARY KEY (id), 
	CONSTRAINT fk_api_keys_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_api_keys_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id), 
	CONSTRAINT uq_api_keys_key_hash UNIQUE (key_hash)
);

CREATE INDEX ix_stack360_api_keys_key_prefix ON stack360.api_keys (key_prefix);

CREATE INDEX ix_stack360_api_keys_workspace_id ON stack360.api_keys (workspace_id);

CREATE TABLE stack360.experience_runs (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	data_source_id UUID NOT NULL, 
	experience_id UUID NOT NULL, 
	external_run_id VARCHAR NOT NULL, 
	visitor_id VARCHAR, 
	person_id UUID, 
	company_id UUID, 
	status VARCHAR NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	last_activity_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	utm_source VARCHAR, 
	utm_medium VARCHAR, 
	utm_campaign VARCHAR, 
	utm_content VARCHAR, 
	utm_term VARCHAR, 
	referrer VARCHAR, 
	landing_url VARCHAR, 
	metadata JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_experience_runs PRIMARY KEY (id), 
	CONSTRAINT uq_experience_runs_source_exp_run UNIQUE (data_source_id, experience_id, external_run_id), 
	CONSTRAINT fk_experience_runs_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_experience_runs_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id), 
	CONSTRAINT fk_experience_runs_experience_id_experiences FOREIGN KEY(experience_id) REFERENCES stack360.experiences (id), 
	CONSTRAINT fk_experience_runs_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id), 
	CONSTRAINT fk_experience_runs_company_id_companies FOREIGN KEY(company_id) REFERENCES stack360.companies (id)
);

CREATE INDEX ix_experience_runs_ws_experience ON stack360.experience_runs (workspace_id, experience_id);

CREATE INDEX ix_experience_runs_ws_person ON stack360.experience_runs (workspace_id, person_id);

CREATE TABLE stack360.ingestion_events (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	data_source_id UUID NOT NULL, 
	external_event_id VARCHAR NOT NULL, 
	schema_version VARCHAR NOT NULL, 
	event_type VARCHAR NOT NULL, 
	occurred_at TIMESTAMP WITH TIME ZONE, 
	received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	payload JSONB NOT NULL, 
	payload_hash VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	processed_at TIMESTAMP WITH TIME ZONE, 
	error_code VARCHAR, 
	error_message TEXT, 
	retry_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_ingestion_events PRIMARY KEY (id), 
	CONSTRAINT uq_ingestion_events_source_extid UNIQUE (data_source_id, external_event_id), 
	CONSTRAINT fk_ingestion_events_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_ingestion_events_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id)
);

CREATE INDEX ix_ingestion_events_event_type ON stack360.ingestion_events (event_type);

CREATE INDEX ix_ingestion_events_received_at ON stack360.ingestion_events (received_at);

CREATE INDEX ix_ingestion_events_workspace_status ON stack360.ingestion_events (workspace_id, status);

CREATE TABLE stack360.person_company_relationships (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	company_id UUID NOT NULL, 
	title VARCHAR, 
	department VARCHAR, 
	role VARCHAR, 
	is_current BOOLEAN, 
	confidence NUMERIC, 
	data_source_id UUID, 
	first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_person_company_relationships PRIMARY KEY (id), 
	CONSTRAINT fk_person_company_relationships_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_person_company_relationships_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id), 
	CONSTRAINT fk_person_company_relationships_company_id_companies FOREIGN KEY(company_id) REFERENCES stack360.companies (id), 
	CONSTRAINT fk_person_company_relationships_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id)
);

CREATE INDEX ix_pcr_workspace_company ON stack360.person_company_relationships (workspace_id, company_id);

CREATE INDEX ix_pcr_workspace_person ON stack360.person_company_relationships (workspace_id, person_id);

CREATE TABLE stack360.person_identities (
	id UUID NOT NULL, 
	person_id UUID NOT NULL, 
	data_source_id UUID, 
	identity_type VARCHAR NOT NULL, 
	value_normalized VARCHAR NOT NULL, 
	value_hash VARCHAR NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	confidence NUMERIC, 
	first_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_person_identities PRIMARY KEY (id), 
	CONSTRAINT fk_person_identities_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id), 
	CONSTRAINT fk_person_identities_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id)
);

CREATE INDEX ix_person_identities_person_id ON stack360.person_identities (person_id);

CREATE INDEX ix_person_identities_value_hash ON stack360.person_identities (value_hash);

CREATE UNIQUE INDEX uq_person_identities_source_scoped ON stack360.person_identities (data_source_id, identity_type, value_hash) WHERE identity_type NOT IN ('email','phone');

CREATE UNIQUE INDEX uq_person_identities_strong_global ON stack360.person_identities (identity_type, value_hash) WHERE identity_type IN ('email','phone');

CREATE TABLE stack360.source_sync_state (
	data_source_id UUID NOT NULL, 
	cursor JSONB, 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	last_success_at TIMESTAMP WITH TIME ZONE, 
	last_error_at TIMESTAMP WITH TIME ZONE, 
	last_error_message TEXT, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_source_sync_state PRIMARY KEY (data_source_id), 
	CONSTRAINT fk_source_sync_state_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id)
);

CREATE TABLE stack360.webhook_endpoints (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	data_source_id UUID NOT NULL, 
	source_key VARCHAR NOT NULL, 
	secret_encrypted BYTEA, 
	secret_key_id VARCHAR, 
	signature_header VARCHAR, 
	signature_scheme VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	mapping JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_webhook_endpoints PRIMARY KEY (id), 
	CONSTRAINT fk_webhook_endpoints_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_webhook_endpoints_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id), 
	CONSTRAINT uq_webhook_endpoints_source_key UNIQUE (source_key)
);

CREATE TABLE stack360.answers (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	run_id UUID NOT NULL, 
	question_key VARCHAR NOT NULL, 
	value JSONB NOT NULL, 
	answer_hash VARCHAR NOT NULL, 
	context JSONB, 
	answered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ingestion_event_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_answers PRIMARY KEY (id), 
	CONSTRAINT fk_answers_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_answers_run_id_experience_runs FOREIGN KEY(run_id) REFERENCES stack360.experience_runs (id), 
	CONSTRAINT fk_answers_ingestion_event_id_ingestion_events FOREIGN KEY(ingestion_event_id) REFERENCES stack360.ingestion_events (id)
);

CREATE INDEX ix_answers_run_question_time ON stack360.answers (run_id, question_key, answered_at);

CREATE TABLE stack360.interactions (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	data_source_id UUID NOT NULL, 
	ingestion_event_id UUID, 
	person_id UUID, 
	company_id UUID, 
	interaction_type VARCHAR NOT NULL, 
	channel VARCHAR, 
	direction VARCHAR, 
	external_interaction_id VARCHAR, 
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	metadata JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_interactions PRIMARY KEY (id), 
	CONSTRAINT fk_interactions_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_interactions_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id), 
	CONSTRAINT fk_interactions_ingestion_event_id_ingestion_events FOREIGN KEY(ingestion_event_id) REFERENCES stack360.ingestion_events (id), 
	CONSTRAINT fk_interactions_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id), 
	CONSTRAINT fk_interactions_company_id_companies FOREIGN KEY(company_id) REFERENCES stack360.companies (id)
);

CREATE INDEX ix_interactions_ws_company_time ON stack360.interactions (workspace_id, company_id, occurred_at);

CREATE INDEX ix_interactions_ws_person_time ON stack360.interactions (workspace_id, person_id, occurred_at);

CREATE UNIQUE INDEX uq_interactions_source_extid ON stack360.interactions (data_source_id, external_interaction_id) WHERE external_interaction_id IS NOT NULL;

CREATE TABLE stack360.observations (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	data_source_id UUID NOT NULL, 
	ingestion_event_id UUID NOT NULL, 
	person_id UUID, 
	company_id UUID, 
	key VARCHAR NOT NULL, 
	value JSONB NOT NULL, 
	value_hash VARCHAR NOT NULL, 
	confidence NUMERIC, 
	source_kind VARCHAR NOT NULL, 
	source_ref VARCHAR, 
	extractor VARCHAR, 
	extractor_version VARCHAR, 
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_observations PRIMARY KEY (id), 
	CONSTRAINT fk_observations_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_observations_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id), 
	CONSTRAINT fk_observations_ingestion_event_id_ingestion_events FOREIGN KEY(ingestion_event_id) REFERENCES stack360.ingestion_events (id), 
	CONSTRAINT fk_observations_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id), 
	CONSTRAINT fk_observations_company_id_companies FOREIGN KEY(company_id) REFERENCES stack360.companies (id)
);

CREATE INDEX ix_observations_ws_company_key ON stack360.observations (workspace_id, company_id, key);

CREATE INDEX ix_observations_ws_person_key ON stack360.observations (workspace_id, person_id, key);

CREATE UNIQUE INDEX uq_observations_same_event ON stack360.observations (ingestion_event_id, coalesce(person_id, '00000000-0000-0000-0000-000000000000'::uuid), coalesce(company_id, '00000000-0000-0000-0000-000000000000'::uuid), key, value_hash);

CREATE TABLE stack360.resolution_cases (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	ingestion_event_id UUID, 
	case_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	severity VARCHAR NOT NULL, 
	subject_type VARCHAR, 
	subject_id UUID, 
	details JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	resolution_action VARCHAR, 
	resolution_payload JSONB, 
	resolved_by_type VARCHAR, 
	resolved_by_ref VARCHAR, 
	CONSTRAINT pk_resolution_cases PRIMARY KEY (id), 
	CONSTRAINT fk_resolution_cases_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_resolution_cases_ingestion_event_id_ingestion_events FOREIGN KEY(ingestion_event_id) REFERENCES stack360.ingestion_events (id)
);

CREATE INDEX ix_resolution_cases_ingestion_event_id ON stack360.resolution_cases (ingestion_event_id);

CREATE INDEX ix_resolution_cases_ws_case_type ON stack360.resolution_cases (workspace_id, case_type);

CREATE INDEX ix_resolution_cases_ws_severity ON stack360.resolution_cases (workspace_id, severity);

CREATE INDEX ix_resolution_cases_ws_status ON stack360.resolution_cases (workspace_id, status);

CREATE UNIQUE INDEX uq_resolution_cases_open_per_event ON stack360.resolution_cases (workspace_id, case_type, ingestion_event_id) WHERE status NOT IN ('resolved','dismissed');

CREATE TABLE stack360.results (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	run_id UUID NOT NULL, 
	result_type VARCHAR NOT NULL, 
	score NUMERIC, 
	verdict VARCHAR, 
	score_band VARCHAR, 
	dimensions JSONB, 
	result JSONB NOT NULL, 
	engine_name VARCHAR, 
	engine_version VARCHAR, 
	result_hash VARCHAR NOT NULL, 
	calculated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ingestion_event_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_results PRIMARY KEY (id), 
	CONSTRAINT fk_results_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_results_run_id_experience_runs FOREIGN KEY(run_id) REFERENCES stack360.experience_runs (id), 
	CONSTRAINT fk_results_ingestion_event_id_ingestion_events FOREIGN KEY(ingestion_event_id) REFERENCES stack360.ingestion_events (id)
);

CREATE INDEX ix_results_run_type_time ON stack360.results (run_id, result_type, calculated_at);

CREATE TABLE stack360.score_history (
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	person_id UUID, 
	company_id UUID, 
	run_id UUID, 
	data_source_id UUID NOT NULL, 
	score_key VARCHAR NOT NULL, 
	score_value NUMERIC NOT NULL, 
	score_band VARCHAR, 
	reason_codes JSONB, 
	engine_name VARCHAR, 
	engine_version VARCHAR, 
	source_ref VARCHAR, 
	calculated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_score_history PRIMARY KEY (id), 
	CONSTRAINT fk_score_history_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id), 
	CONSTRAINT fk_score_history_person_id_people FOREIGN KEY(person_id) REFERENCES stack360.people (id), 
	CONSTRAINT fk_score_history_company_id_companies FOREIGN KEY(company_id) REFERENCES stack360.companies (id), 
	CONSTRAINT fk_score_history_run_id_experience_runs FOREIGN KEY(run_id) REFERENCES stack360.experience_runs (id), 
	CONSTRAINT fk_score_history_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id)
);

CREATE INDEX ix_score_history_ws_company_key_time ON stack360.score_history (workspace_id, company_id, score_key, calculated_at);

CREATE INDEX ix_score_history_ws_person_key_time ON stack360.score_history (workspace_id, person_id, score_key, calculated_at);

CREATE TABLE stack360.resolution_recommendations (
	id UUID NOT NULL, 
	resolution_case_id UUID NOT NULL, 
	recommended_action VARCHAR NOT NULL, 
	candidate_entity_ids JSONB NOT NULL, 
	confidence NUMERIC, 
	evidence JSONB NOT NULL, 
	summary TEXT, 
	agent_name VARCHAR, 
	agent_version VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_resolution_recommendations PRIMARY KEY (id), 
	CONSTRAINT fk_resolution_recommendations_resolution_case_id_resolu_3ad1 FOREIGN KEY(resolution_case_id) REFERENCES stack360.resolution_cases (id)
);

CREATE INDEX ix_resolution_recommendations_case_id ON stack360.resolution_recommendations (resolution_case_id);
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS stack360")
    op.execute(STACK360_DDL)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS stack360 CASCADE")

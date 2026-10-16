"""stack360 raw_envelopes — cópia durável do bruto lido de qualquer fonte

Revision ID: c7f1a9e2b4d6
Revises: aa47386e4e9f
Create Date: 2026-10-16

MANUAL, ADITIVA. Só adiciona a tabela ``stack360.raw_envelopes``. Não toca
em nenhuma tabela existente. Sem rota REST expõe essa tabela — acesso só
por quem tem credencial direta no banco (motor de projeção + auditoria).
"""
from alembic import op

revision = "c7f1a9e2b4d6"
down_revision = "aa47386e4e9f"
branch_labels = None
depends_on = None

RAW_ENVELOPES_DDL = r"""
CREATE TABLE stack360.raw_envelopes (
	id UUID NOT NULL,
	workspace_id UUID NOT NULL,
	data_source_id UUID NOT NULL,
	external_key VARCHAR NOT NULL,
	envelope_type VARCHAR NOT NULL,
	content JSONB NOT NULL,
	content_hash VARCHAR NOT NULL,
	fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_raw_envelopes PRIMARY KEY (id),
	CONSTRAINT uq_raw_envelopes_source_extkey UNIQUE (data_source_id, external_key),
	CONSTRAINT fk_raw_envelopes_workspace_id_workspaces FOREIGN KEY(workspace_id) REFERENCES stack360.workspaces (id),
	CONSTRAINT fk_raw_envelopes_data_source_id_data_sources FOREIGN KEY(data_source_id) REFERENCES stack360.data_sources (id)
);

CREATE INDEX ix_raw_envelopes_ws_source ON stack360.raw_envelopes (workspace_id, data_source_id);
"""


def upgrade() -> None:
    op.execute(RAW_ENVELOPES_DDL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stack360.raw_envelopes")

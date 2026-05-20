"""add_contact_evidence_and_enrichment_state

Revision ID: 018556ee6333
Revises:
Create Date: 2026-05-18 11:59:12.709038

NOTE: contact_evidence is owned by the 'postgres' superuser role.
The ADD COLUMN and CREATE INDEX operations on that table must be run
by a superuser (or after GRANT OWNERSHIP to stakeholder_app_dev).
This migration only creates the brand-new enrichment_state table.
The contact_evidence DDL below is included for documentation; it is
skipped at runtime if the current user lacks table ownership.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '018556ee6333'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _contact_evidence_owned_by_current_user(conn) -> bool:
    """Return True if the migration user owns contact_evidence."""
    result = conn.execute(
        sa.text(
            "SELECT tableowner = current_user "
            "FROM pg_tables WHERE tablename = 'contact_evidence'"
        )
    )
    row = result.fetchone()
    return bool(row and row[0])


def upgrade() -> None:
    # 1. Create enrichment_state — always safe (new table)
    op.create_table(
        'enrichment_state',
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('last_enriched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('entity_type', 'entity_id'),
    )

    # 2. contact_evidence changes — only if the current user owns the table.
    #    In production environments where the table was created by postgres,
    #    run the equivalent SQL as a superuser after the migration:
    #
    #    ALTER TABLE contact_evidence ADD COLUMN IF NOT EXISTS conversation_id VARCHAR;
    #    ALTER TABLE contact_evidence ADD COLUMN IF NOT EXISTS payload JSONB;
    #    CREATE INDEX IF NOT EXISTS ix_contact_evidence_contact_id ON contact_evidence(contact_id);
    #    CREATE INDEX IF NOT EXISTS ix_contact_evidence_evidence_type ON contact_evidence(evidence_type);
    #    CREATE INDEX IF NOT EXISTS ix_contact_evidence_conversation_id ON contact_evidence(conversation_id);
    #    CREATE INDEX IF NOT EXISTS ix_contact_evidence_message_id ON contact_evidence(message_id);
    bind = op.get_bind()
    if _contact_evidence_owned_by_current_user(bind):
        op.add_column('contact_evidence', sa.Column('conversation_id', sa.String(), nullable=True))
        op.add_column('contact_evidence', sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.create_index('ix_contact_evidence_contact_id', 'contact_evidence', ['contact_id'])
        op.create_index('ix_contact_evidence_evidence_type', 'contact_evidence', ['evidence_type'])
        op.create_index('ix_contact_evidence_conversation_id', 'contact_evidence', ['conversation_id'])
        op.create_index('ix_contact_evidence_message_id', 'contact_evidence', ['message_id'])


def downgrade() -> None:
    bind = op.get_bind()
    if _contact_evidence_owned_by_current_user(bind):
        op.drop_index('ix_contact_evidence_message_id', table_name='contact_evidence')
        op.drop_index('ix_contact_evidence_conversation_id', table_name='contact_evidence')
        op.drop_index('ix_contact_evidence_evidence_type', table_name='contact_evidence')
        op.drop_index('ix_contact_evidence_contact_id', table_name='contact_evidence')
        op.drop_column('contact_evidence', 'payload')
        op.drop_column('contact_evidence', 'conversation_id')
    op.drop_table('enrichment_state')

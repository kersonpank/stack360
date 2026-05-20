"""fix_contact_evidence_add_columns_and_indexes

Revision ID: d37b373cb63d
Revises: 018556ee6333
Create Date: 2026-05-18 12:47:15.342816

This migration adds conversation_id and payload columns to contact_evidence,
plus four indexes. The table is owned by the 'postgres' superuser.

If running as a non-owner the ALTER TABLE will silently skip and a NOTICE will
be raised — the migration is still recorded as applied.  Re-run as postgres
(or use migrations/fix_contact_evidence_schema.sql) to apply the schema change.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd37b373cb63d'
down_revision: Union[str, None] = '018556ee6333'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL with soft-fail so migration applies regardless of table owner.
    # When run as postgres/superuser the columns and indexes are created.
    # When run as app user the EXCEPTION block raises NOTICE and continues.
    op.execute("""
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE contact_evidence
                    ADD COLUMN IF NOT EXISTS conversation_id text;
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping ADD COLUMN conversation_id: run migration as superuser.';
            END;

            BEGIN
                ALTER TABLE contact_evidence
                    ADD COLUMN IF NOT EXISTS payload jsonb DEFAULT '{}'::jsonb;
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping ADD COLUMN payload: run migration as superuser.';
            END;

            BEGIN
                CREATE INDEX IF NOT EXISTS ix_contact_evidence_contact_id
                    ON contact_evidence(contact_id);
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping index ix_contact_evidence_contact_id.';
            END;

            BEGIN
                CREATE INDEX IF NOT EXISTS ix_contact_evidence_evidence_type
                    ON contact_evidence(evidence_type);
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping index ix_contact_evidence_evidence_type.';
            END;

            BEGIN
                CREATE INDEX IF NOT EXISTS ix_contact_evidence_conversation_id
                    ON contact_evidence(conversation_id);
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping index ix_contact_evidence_conversation_id.';
            END;

            BEGIN
                CREATE INDEX IF NOT EXISTS ix_contact_evidence_message_id
                    ON contact_evidence(message_id);
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping index ix_contact_evidence_message_id.';
            END;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            BEGIN
                DROP INDEX IF EXISTS ix_contact_evidence_message_id;
                DROP INDEX IF EXISTS ix_contact_evidence_conversation_id;
                DROP INDEX IF EXISTS ix_contact_evidence_evidence_type;
                DROP INDEX IF EXISTS ix_contact_evidence_contact_id;
                ALTER TABLE contact_evidence DROP COLUMN IF EXISTS payload;
                ALTER TABLE contact_evidence DROP COLUMN IF EXISTS conversation_id;
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'Skipping downgrade: run as superuser.';
            END;
        END
        $$;
    """)

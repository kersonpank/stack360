"""add_stakeholder_actions

Revision ID: 13b31f818410
Revises: d37b373cb63d
Create Date: 2026-05-20 15:12:47.059340

"""
from typing import Sequence, Union

from alembic import op


revision: str = '13b31f818410'
down_revision: Union[str, None] = 'd37b373cb63d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS stakeholder_actions (
            action_id   bigserial PRIMARY KEY,
            contact_id  text NOT NULL,
            conversation_id text NULL,
            opportunity_id  bigint NULL,
            action_type text NOT NULL,
            title       text NOT NULL,
            description text NULL,
            priority_score numeric DEFAULT 0,
            reason      text NULL,
            status      text DEFAULT 'nova',
            assigned_to text NULL,
            due_at      timestamptz NULL,
            source      text DEFAULT 'rules',
            payload     jsonb DEFAULT '{}'::jsonb,
            created_at  timestamptz DEFAULT now(),
            updated_at  timestamptz DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_sa_contact_id      ON stakeholder_actions(contact_id);
        CREATE INDEX IF NOT EXISTS idx_sa_action_type     ON stakeholder_actions(action_type);
        CREATE INDEX IF NOT EXISTS idx_sa_status          ON stakeholder_actions(status);
        CREATE INDEX IF NOT EXISTS idx_sa_priority_score  ON stakeholder_actions(priority_score DESC);
        CREATE INDEX IF NOT EXISTS idx_sa_due_at          ON stakeholder_actions(due_at);
        CREATE INDEX IF NOT EXISTS idx_sa_opportunity_id  ON stakeholder_actions(opportunity_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stakeholder_actions CASCADE;")

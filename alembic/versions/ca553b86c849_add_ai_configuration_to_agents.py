"""Add AI configuration to agents

Revision ID: ca553b86c849
Revises: 5a8e64824892
Create Date: 2026-01-20 15:03:50.706647

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ca553b86c849'
down_revision = '5a8e64824892'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add AI configuration columns to agent_configs
    op.add_column('agent_configs', sa.Column('ai_mode', sa.String(), server_default='simple', nullable=False))
    op.add_column('agent_configs', sa.Column('ai_system_prompt', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('ai_provider', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('ai_api_key_encrypted', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('ai_model', sa.String(), nullable=True))
    op.add_column('agent_configs', sa.Column('ai_endpoint', sa.String(), nullable=True))


def downgrade() -> None:
    # Remove AI configuration columns from agent_configs
    op.drop_column('agent_configs', 'ai_endpoint')
    op.drop_column('agent_configs', 'ai_model')
    op.drop_column('agent_configs', 'ai_api_key_encrypted')
    op.drop_column('agent_configs', 'ai_provider')
    op.drop_column('agent_configs', 'ai_system_prompt')
    op.drop_column('agent_configs', 'ai_mode')

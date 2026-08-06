"""add extra_metadata and tags to receipts

Revision ID: 5cc008275fb1
Revises: d8f9c3b21456
Create Date: 2026-05-01

"""
from alembic import op
import sqlalchemy as sa

revision = "5cc008275fb1"
down_revision = "d8f9c3b21456"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("receipts", sa.Column("extra_metadata", sa.JSON(), nullable=True))
    op.add_column("receipts", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("receipts", "tags")
    op.drop_column("receipts", "extra_metadata")

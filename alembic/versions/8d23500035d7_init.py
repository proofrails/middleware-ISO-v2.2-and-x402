"""init

Revision ID: 8d23500035d7
Revises:
Create Date: 2025-12-18 15:44:30.259971

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# Import app models to reuse GUID TypeDecorator
from app import models as app_models

# revision identifiers, used by Alembic.
revision = "8d23500035d7"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tables from scratch (baseline).

    op.create_table(
        "projects",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner_wallet", sa.String(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_projects_owner_wallet"), "projects", ["owner_wallet"], unique=False)

    op.create_table(
        "receipts",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", app_models.GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("tip_tx_hash", sa.String(), nullable=False),
        sa.Column("chain", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("sender_wallet", sa.String(), nullable=False),
        sa.Column("receiver_wallet", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("bundle_hash", sa.String(), nullable=True),
        sa.Column("flare_txid", sa.String(), nullable=True),
        sa.Column("xml_path", sa.String(), nullable=True),
        sa.Column("bundle_path", sa.String(), nullable=True),
        sa.Column("refund_of", app_models.GUID(), sa.ForeignKey("receipts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("reference"),
        sa.UniqueConstraint("chain", "tip_tx_hash", name="uq_chain_tip"),
    )
    op.create_index(op.f("ix_receipts_project_id"), "receipts", ["project_id"], unique=False)

    op.create_table(
        "iso_artifacts",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("receipt_id", app_models.GUID(), sa.ForeignKey("receipts.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_iso_artifacts_receipt_id"), "iso_artifacts", ["receipt_id"], unique=False)

    op.create_table(
        "chain_anchors",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("receipt_id", app_models.GUID(), sa.ForeignKey("receipts.id"), nullable=False),
        sa.Column("chain", sa.String(), nullable=False),
        sa.Column("txid", sa.String(), nullable=False),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_chain_anchors_receipt_id"), "chain_anchors", ["receipt_id"], unique=False)

    op.create_table(
        "org_config",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", app_models.GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("role", sa.String(), server_default="project_admin", nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_project_id"), "api_keys", ["project_id"], unique=False)

    op.create_table(
        "linked_wallets",
        sa.Column("id", app_models.GUID(), primary_key=True, nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("address"),
    )
    op.create_index(op.f("ix_linked_wallets_address"), "linked_wallets", ["address"], unique=True)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index(op.f("ix_linked_wallets_address"), table_name="linked_wallets")
    op.drop_table("linked_wallets")

    op.drop_index(op.f("ix_api_keys_project_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_table("org_config")

    op.drop_index(op.f("ix_chain_anchors_receipt_id"), table_name="chain_anchors")
    op.drop_table("chain_anchors")

    op.drop_index(op.f("ix_iso_artifacts_receipt_id"), table_name="iso_artifacts")
    op.drop_table("iso_artifacts")

    op.drop_index(op.f("ix_receipts_project_id"), table_name="receipts")
    op.drop_table("receipts")

    op.drop_index(op.f("ix_projects_owner_wallet"), table_name="projects")
    op.drop_table("projects")

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "5a8e64824892"
down_revision = "8d23500035d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protected_endpoints",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("currency", sa.String(), server_default="USDC", nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("enabled", sa.String(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path"),
    )

    op.create_table(
        "agent_configs",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("wallet_address", sa.String(), nullable=False),
        sa.Column("xmtp_address", sa.String(), nullable=True),
        sa.Column("pricing_rules", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("project_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_configs_project_id"), "agent_configs", ["project_id"], unique=False)
    op.create_index(op.f("ix_agent_configs_wallet_address"), "agent_configs", ["wallet_address"], unique=False)

    op.create_table(
        "x402_payments",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("tx_hash", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("currency", sa.String(), server_default="USDC", nullable=False),
        sa.Column("chain", sa.String(), server_default="base", nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("agent_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_x402_payments_agent_id"), "x402_payments", ["agent_id"], unique=False)
    op.create_index(op.f("ix_x402_payments_tx_hash"), "x402_payments", ["tx_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_x402_payments_tx_hash"), table_name="x402_payments")
    op.drop_index(op.f("ix_x402_payments_agent_id"), table_name="x402_payments")
    op.drop_table("x402_payments")

    op.drop_index(op.f("ix_agent_configs_wallet_address"), table_name="agent_configs")
    op.drop_index(op.f("ix_agent_configs_project_id"), table_name="agent_configs")
    op.drop_table("agent_configs")

    op.drop_table("protected_endpoints")

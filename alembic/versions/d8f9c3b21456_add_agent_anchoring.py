from alembic import op
import sqlalchemy as sa


revision = "d8f9c3b21456"
down_revision = "ca553b86c849"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_anchors",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("bundle_hash", sa.String(), nullable=False),
        sa.Column("anchor_txid", sa.String(), nullable=True),
        sa.Column("chain", sa.String(), nullable=False, server_default="flare"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_configs.id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["receipts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_anchors_agent_id", "agent_anchors", ["agent_id"])
    op.create_index("ix_agent_anchors_status", "agent_anchors", ["status"])

    op.add_column("agent_configs", sa.Column("anchor_wallet_address", sa.String(), nullable=True))
    op.add_column("agent_configs", sa.Column("anchor_private_key_encrypted", sa.String(), nullable=True))
    op.add_column("agent_configs", sa.Column("auto_anchor_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("agent_configs", sa.Column("anchor_on_payment", sa.Boolean(), server_default="false", nullable=False))

    op.add_column("x402_payments", sa.Column("anchor_txid", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("anchor_status", sa.String(), nullable=True))
    op.create_index("ix_x402_payments_anchor_status", "x402_payments", ["anchor_status"])


def downgrade():
    op.drop_index("ix_x402_payments_anchor_status", table_name="x402_payments")
    op.drop_column("x402_payments", "anchor_status")
    op.drop_column("x402_payments", "anchor_txid")

    op.drop_column("agent_configs", "anchor_on_payment")
    op.drop_column("agent_configs", "auto_anchor_enabled")
    op.drop_column("agent_configs", "anchor_private_key_encrypted")
    op.drop_column("agent_configs", "anchor_wallet_address")

    op.drop_index("ix_agent_anchors_status", table_name="agent_anchors")
    op.drop_index("ix_agent_anchors_agent_id", table_name="agent_anchors")
    op.drop_table("agent_anchors")

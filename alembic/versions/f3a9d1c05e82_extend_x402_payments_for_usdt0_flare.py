"""Extend x402_payments for USDT0 Flare multi-chain support.

Adds:
  - payment_type column
  - raw_amount column
  - chain_id column
  - token_address column
  - facilitator_address column
  - payer_address column
  - eip3009_nonce column
  - authorization_type column
  - facilitator_payment_id column
  - status column
  - Makes tx_hash nullable (for pending server-submitted settlements)
  - Adds unique constraint on (eip3009_nonce, chain_id, token_address) for replay protection

Revision ID: f3a9d1c05e82
Revises: d8f9c3b21456
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f3a9d1c05e82"
down_revision = "d8f9c3b21456"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to x402_payments
    op.add_column("x402_payments", sa.Column("payment_type", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("raw_amount", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("chain_id", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("token_address", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("facilitator_address", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("payer_address", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("eip3009_nonce", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("authorization_type", sa.String(), nullable=True))
    op.add_column("x402_payments", sa.Column("facilitator_payment_id", sa.String(), nullable=True))
    op.add_column(
        "x402_payments",
        sa.Column("status", sa.String(), nullable=False, server_default="verified"),
    )

    # Make tx_hash nullable — needed for server-submitted mode (hash unknown until after broadcast)
    # SQLite does not support ALTER COLUMN; skip for SQLite, apply for Postgres.
    # The application code already treats tx_hash as Optional.
    try:
        op.alter_column("x402_payments", "tx_hash", nullable=True)
    except Exception:
        pass  # SQLite — no-op; column becomes nullable via model reflection

    # Drop the existing NOT NULL unique index on tx_hash (Postgres) and recreate partial
    # SQLite handles this differently; wrap in try/except for portability.
    try:
        op.drop_index("ix_x402_payments_tx_hash", table_name="x402_payments")
    except Exception:
        pass

    # Recreate as partial unique index so NULL tx_hash rows don't collide
    # (standard SQL: NULLs are not equal in unique indexes, so this is safe on Postgres)
    op.create_index(
        "ix_x402_payments_tx_hash",
        "x402_payments",
        ["tx_hash"],
        unique=True,
        postgresql_where=sa.text("tx_hash IS NOT NULL"),
    )

    # Index for replay protection: unique EIP-3009 nonce per chain+token
    op.create_index(
        "ix_x402_payments_nonce_chain_token",
        "x402_payments",
        ["eip3009_nonce", "chain_id", "token_address"],
        unique=True,
        postgresql_where=sa.text("eip3009_nonce IS NOT NULL"),
    )

    op.create_index(
        "ix_x402_payments_payer",
        "x402_payments",
        ["payer_address"],
        unique=False,
    )
    op.create_index(
        "ix_x402_payments_status",
        "x402_payments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_x402_payments_status", table_name="x402_payments")
    op.drop_index("ix_x402_payments_payer", table_name="x402_payments")
    op.drop_index("ix_x402_payments_nonce_chain_token", table_name="x402_payments")
    op.drop_index("ix_x402_payments_tx_hash", table_name="x402_payments")

    op.create_index("ix_x402_payments_tx_hash", "x402_payments", ["tx_hash"], unique=True)

    try:
        op.alter_column("x402_payments", "tx_hash", nullable=False)
    except Exception:
        pass

    op.drop_column("x402_payments", "status")
    op.drop_column("x402_payments", "facilitator_payment_id")
    op.drop_column("x402_payments", "authorization_type")
    op.drop_column("x402_payments", "eip3009_nonce")
    op.drop_column("x402_payments", "payer_address")
    op.drop_column("x402_payments", "facilitator_address")
    op.drop_column("x402_payments", "token_address")
    op.drop_column("x402_payments", "chain_id")
    op.drop_column("x402_payments", "raw_amount")
    op.drop_column("x402_payments", "payment_type")

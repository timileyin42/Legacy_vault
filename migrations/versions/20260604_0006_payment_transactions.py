"""paystack payment transactions

Revision ID: 20260604_0006
Revises: 20260604_0005
Create Date: 2026-06-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0006"
down_revision = "20260604_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    payment_status = postgresql.ENUM(
        "pending", "success", "failed", "abandoned", name="paymentstatus", create_type=False
    )
    payment_status.create(bind, checkfirst=True)
    # plantier / billingcycle already exist (created in 0003); reuse without re-creating.
    plan_tier = postgresql.ENUM("free", "premium", "family", name="plantier", create_type=False)
    billing_cycle = postgresql.ENUM("monthly", "yearly", name="billingcycle", create_type=False)

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.String(length=80), nullable=False),
        sa.Column("plan", plan_tier, nullable=False),
        sa.Column("billing_cycle", billing_cycle, nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("access_code", sa.String(length=120), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_transactions_is_deleted", "payment_transactions", ["is_deleted"])
    op.create_index("ix_payment_transactions_owner_id", "payment_transactions", ["owner_id"])
    op.create_index("ix_payment_transactions_public_id", "payment_transactions", ["public_id"], unique=True)
    op.create_index("ix_payment_transactions_reference", "payment_transactions", ["reference"], unique=True)
    op.create_index("ix_payment_transactions_status", "payment_transactions", ["status"])


def downgrade() -> None:
    op.drop_table("payment_transactions")
    sa.Enum(name="paymentstatus").drop(op.get_bind(), checkfirst=True)

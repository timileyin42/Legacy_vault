"""password reset codes (forgot/reset password flow)

Revision ID: 20260604_0005
Revises: 20260604_0004
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0005"
down_revision = "20260604_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_password_reset_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_identity_password_reset_codes_user_id", "identity_password_reset_codes", ["user_id"]
    )
    op.create_index(
        "ix_identity_password_reset_codes_code_hash", "identity_password_reset_codes", ["code_hash"]
    )


def downgrade() -> None:
    op.drop_table("identity_password_reset_codes")

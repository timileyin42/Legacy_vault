"""google sign-in (auth provider) + email verification codes

Revision ID: 20260604_0004
Revises: 20260604_0003
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0004"
down_revision = "20260604_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    auth_provider = postgresql.ENUM("email", "google", name="authprovider", create_type=False)
    auth_provider.create(bind, checkfirst=True)

    op.add_column(
        "identity_users",
        sa.Column("auth_provider", auth_provider, server_default="email", nullable=False),
    )
    op.add_column("identity_users", sa.Column("firebase_uid", sa.String(length=128), nullable=True))
    op.add_column(
        "identity_users",
        sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(
        "ix_identity_users_firebase_uid", "identity_users", ["firebase_uid"], unique=True
    )

    op.create_table(
        "identity_email_verification_codes",
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
        "ix_identity_email_verification_codes_user_id",
        "identity_email_verification_codes",
        ["user_id"],
    )
    op.create_index(
        "ix_identity_email_verification_codes_code_hash",
        "identity_email_verification_codes",
        ["code_hash"],
    )


def downgrade() -> None:
    op.drop_table("identity_email_verification_codes")
    op.drop_index("ix_identity_users_firebase_uid", table_name="identity_users")
    op.drop_column("identity_users", "email_verified")
    op.drop_column("identity_users", "firebase_uid")
    op.drop_column("identity_users", "auth_provider")
    sa.Enum(name="authprovider").drop(op.get_bind(), checkfirst=True)

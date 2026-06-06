"""document storage metadata

Revision ID: 20260604_0002
Revises: 20260604_0001
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0002"
down_revision = "20260604_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vault_documents", sa.Column("file_name", sa.String(length=255), nullable=True))
    op.add_column("vault_documents", sa.Column("content_type", sa.String(length=120), nullable=True))
    op.add_column("vault_documents", sa.Column("byte_size", sa.Integer(), nullable=True))
    op.add_column(
        "vault_documents",
        sa.Column("storage_provider", sa.String(length=80), server_default="cloudflare_r2", nullable=False),
    )
    op.add_column(
        "vault_documents",
        sa.Column("integrity_status", sa.String(length=40), server_default="verified", nullable=False),
    )
    op.add_column("vault_documents", sa.Column("notarization_status", sa.String(length=80), nullable=True))
    op.add_column("vault_documents", sa.Column("ocr_text_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "vault_documents",
        sa.Column("version_count", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("vault_documents", "version_count")
    op.drop_column("vault_documents", "ocr_text_encrypted")
    op.drop_column("vault_documents", "notarization_status")
    op.drop_column("vault_documents", "integrity_status")
    op.drop_column("vault_documents", "storage_provider")
    op.drop_column("vault_documents", "byte_size")
    op.drop_column("vault_documents", "content_type")
    op.drop_column("vault_documents", "file_name")

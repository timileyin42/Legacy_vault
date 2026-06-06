"""initial backend schema

Revision ID: 20260604_0001
Revises:
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0001"
down_revision = None
branch_labels = None
depends_on = None


def _uuid() -> sa.Uuid:
    return sa.Uuid()


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _audit_soft_delete() -> list[sa.Column]:
    return [
        sa.Column("created_by", _uuid(), nullable=True),
        sa.Column("updated_by", _uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _public_id() -> sa.Column:
    return sa.Column("public_id", sa.String(length=32), nullable=False)


def upgrade() -> None:
    user_role = sa.Enum("user", "admin", name="userrole")
    vault_category = sa.Enum(
        "bank_account",
        "investment",
        "crypto_wallet",
        "insurance_policy",
        "property_record",
        "business_ownership",
        "subscription",
        "intellectual_property",
        "social_media",
        "personal_note",
        "family_record",
        "password",
        "legal_document",
        name="vaultcategory",
    )
    security_level = sa.Enum("standard", "high", "critical", name="securitylevel")
    beneficiary_status = sa.Enum(
        "pending_verification", "verified", "suspended", name="beneficiarystatus"
    )
    release_trigger = sa.Enum(
        "death_verification",
        "incapacity_verification",
        "age_reached",
        "scheduled_date",
        "manual_release",
        name="releasetrigger",
    )
    access_request_status = sa.Enum(
        "submitted",
        "identity_verification",
        "evidence_review",
        "waiting_period",
        "approved",
        "rejected",
        "released",
        name="accessrequeststatus",
    )
    audit_action = sa.Enum(
        "user_registered",
        "user_login",
        "vault_item_created",
        "vault_item_viewed",
        "beneficiary_created",
        "access_request_created",
        "access_request_status_changed",
        name="auditaction",
    )

    op.create_table(
        "identity_users",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False),
        sa.Column("mfa_secret_encrypted", sa.String(length=512), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_users_email", "identity_users", ["email"], unique=True)
    op.create_index("ix_identity_users_is_deleted", "identity_users", ["is_deleted"])
    op.create_index("ix_identity_users_public_id", "identity_users", ["public_id"], unique=True)

    op.create_table(
        "identity_user_sessions",
        sa.Column("id", _uuid(), nullable=False),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("user_id", _uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("device_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_user_sessions_is_deleted", "identity_user_sessions", ["is_deleted"])
    op.create_index("ix_identity_user_sessions_refresh_token_hash", "identity_user_sessions", ["refresh_token_hash"], unique=True)
    op.create_index("ix_identity_user_sessions_user_id", "identity_user_sessions", ["user_id"])

    op.create_table(
        "vault_items",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("category", vault_category, nullable=False),
        sa.Column("title_encrypted", sa.Text(), nullable=False),
        sa.Column("payload_encrypted", sa.Text(), nullable=False),
        sa.Column("masked_hint", sa.String(length=128), nullable=True),
        sa.Column("security_level", security_level, nullable=False),
        sa.Column("release_policy", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_items_category", "vault_items", ["category"])
    op.create_index("ix_vault_items_is_deleted", "vault_items", ["is_deleted"])
    op.create_index("ix_vault_items_owner_id", "vault_items", ["owner_id"])
    op.create_index("ix_vault_items_public_id", "vault_items", ["public_id"], unique=True)

    op.create_table(
        "vault_assets",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("vault_item_id", _uuid(), nullable=True),
        sa.Column("category", vault_category, nullable=False),
        sa.Column("name_encrypted", sa.Text(), nullable=False),
        sa.Column("value_estimate", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("metadata_encrypted", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.ForeignKeyConstraint(["vault_item_id"], ["vault_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_assets_category", "vault_assets", ["category"])
    op.create_index("ix_vault_assets_is_deleted", "vault_assets", ["is_deleted"])
    op.create_index("ix_vault_assets_owner_id", "vault_assets", ["owner_id"])
    op.create_index("ix_vault_assets_public_id", "vault_assets", ["public_id"], unique=True)

    op.create_table(
        "vault_documents",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("title_encrypted", sa.Text(), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("storage_object_encrypted", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("classification", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_documents_document_type", "vault_documents", ["document_type"])
    op.create_index("ix_vault_documents_is_deleted", "vault_documents", ["is_deleted"])
    op.create_index("ix_vault_documents_owner_id", "vault_documents", ["owner_id"])
    op.create_index("ix_vault_documents_public_id", "vault_documents", ["public_id"], unique=True)

    op.create_table(
        "beneficiaries",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("full_name_encrypted", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("relationship", sa.String(length=80), nullable=False),
        sa.Column("status", beneficiary_status, nullable=False),
        sa.Column("allocation_percent", sa.Integer(), nullable=False),
        sa.Column("instructions_encrypted", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_beneficiaries_email", "beneficiaries", ["email"])
    op.create_index("ix_beneficiaries_is_deleted", "beneficiaries", ["is_deleted"])
    op.create_index("ix_beneficiaries_owner_id", "beneficiaries", ["owner_id"])
    op.create_index("ix_beneficiaries_public_id", "beneficiaries", ["public_id"], unique=True)

    op.create_table(
        "trusted_contacts",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("full_name_encrypted", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_encrypted", sa.Text(), nullable=True),
        sa.Column("verification_weight", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trusted_contacts_email", "trusted_contacts", ["email"])
    op.create_index("ix_trusted_contacts_is_deleted", "trusted_contacts", ["is_deleted"])
    op.create_index("ix_trusted_contacts_owner_id", "trusted_contacts", ["owner_id"])
    op.create_index("ix_trusted_contacts_public_id", "trusted_contacts", ["public_id"], unique=True)

    op.create_table(
        "inheritance_rules",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("beneficiary_id", _uuid(), nullable=False),
        sa.Column("vault_item_id", _uuid(), nullable=True),
        sa.Column("trigger", release_trigger, nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("instructions_encrypted", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.ForeignKeyConstraint(["vault_item_id"], ["vault_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inheritance_rules_beneficiary_id", "inheritance_rules", ["beneficiary_id"])
    op.create_index("ix_inheritance_rules_is_deleted", "inheritance_rules", ["is_deleted"])
    op.create_index("ix_inheritance_rules_owner_id", "inheritance_rules", ["owner_id"])
    op.create_index("ix_inheritance_rules_public_id", "inheritance_rules", ["public_id"], unique=True)
    op.create_index("ix_inheritance_rules_trigger", "inheritance_rules", ["trigger"])

    op.create_table(
        "access_requests",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("beneficiary_id", _uuid(), nullable=False),
        sa.Column("request_type", release_trigger, nullable=False),
        sa.Column("status", access_request_status, nullable=False),
        sa.Column("evidence_summary_encrypted", sa.Text(), nullable=True),
        sa.Column("waiting_period_days", sa.Integer(), nullable=False),
        sa.Column("release_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes_encrypted", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_requests_beneficiary_id", "access_requests", ["beneficiary_id"])
    op.create_index("ix_access_requests_is_deleted", "access_requests", ["is_deleted"])
    op.create_index("ix_access_requests_owner_id", "access_requests", ["owner_id"])
    op.create_index("ix_access_requests_public_id", "access_requests", ["public_id"], unique=True)
    op.create_index("ix_access_requests_request_type", "access_requests", ["request_type"])
    op.create_index("ix_access_requests_status", "access_requests", ["status"])

    op.create_table(
        "security_audit_logs",
        sa.Column("id", _uuid(), nullable=False),
        *_timestamps(),
        sa.Column("actor_id", _uuid(), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_public_id", sa.String(length=32), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_audit_logs_action", "security_audit_logs", ["action"])
    op.create_index("ix_security_audit_logs_actor_id", "security_audit_logs", ["actor_id"])


def downgrade() -> None:
    op.drop_table("security_audit_logs")
    op.drop_table("access_requests")
    op.drop_table("inheritance_rules")
    op.drop_table("trusted_contacts")
    op.drop_table("beneficiaries")
    op.drop_table("vault_documents")
    op.drop_table("vault_assets")
    op.drop_table("vault_items")
    op.drop_table("identity_user_sessions")
    op.drop_table("identity_users")

    for enum_name in [
        "auditaction",
        "accessrequeststatus",
        "releasetrigger",
        "beneficiarystatus",
        "securitylevel",
        "vaultcategory",
        "userrole",
    ]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)


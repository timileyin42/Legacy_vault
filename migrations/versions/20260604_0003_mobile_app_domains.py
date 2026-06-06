"""mobile app domains: profile, notifications, subscriptions, verification, legacy, succession

Revision ID: 20260604_0003
Revises: 20260604_0002
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260604_0003"
down_revision = "20260604_0002"
branch_labels = None
depends_on = None


_NEW_AUDIT_ACTIONS = [
    "user_logout",
    "profile_updated",
    "security_settings_changed",
    "session_revoked",
    "device_registered",
    "vault_item_updated",
    "vault_item_deleted",
    "asset_updated",
    "asset_deleted",
    "document_deleted",
    "beneficiary_updated",
    "beneficiary_deleted",
    "trusted_contact_created",
    "inheritance_rule_updated",
    "legacy_note_created",
    "subscription_changed",
    "death_verification_submitted",
    "succession_report_generated",
]


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
    return sa.Column("public_id", sa.String(length=32), nullable=True)


def _std_indexes(table: str) -> None:
    op.create_index(f"ix_{table}_is_deleted", table, ["is_deleted"])
    op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])
    op.create_index(f"ix_{table}_public_id", table, ["public_id"], unique=True)


def upgrade() -> None:
    bind = op.get_bind()

    # postgresql.ENUM(create_type=False): we create each type once explicitly below
    # (idempotent via checkfirst), so create_table must not also emit CREATE TYPE for
    # these shared enums. create_type=False is only honoured on the PG ENUM type.
    device_platform = postgresql.ENUM("ios", "android", "web", name="deviceplatform", create_type=False)
    notification_category = postgresql.ENUM(
        "security_alert", "inheritance_event", "access_request", "document", "system",
        name="notificationcategory", create_type=False,
    )
    plan_tier = postgresql.ENUM("free", "premium", "family", name="plantier", create_type=False)
    billing_cycle = postgresql.ENUM("monthly", "yearly", name="billingcycle", create_type=False)
    subscription_status = postgresql.ENUM("active", "canceled", name="subscriptionstatus", create_type=False)
    verification_status = postgresql.ENUM(
        "in_progress", "completed", "rejected", name="verificationstatus", create_type=False
    )
    stage_status = postgresql.ENUM("pending", "validated", "failed", name="stagestatus", create_type=False)
    witness_status = postgresql.ENUM("pending", "verified", "declined", name="witnessstatus", create_type=False)
    media_type = postgresql.ENUM("written", "audio", "video", name="mediatype", create_type=False)
    legacy_release_trigger = postgresql.ENUM(
        "specific_date", "proof_of_death", "anniversary", "event", name="legacyreleasetrigger", create_type=False
    )
    legacy_note_status = postgresql.ENUM("draft", "scheduled", name="legacynotestatus", create_type=False)
    succession_status = postgresql.ENUM(
        "draft", "verified_released", name="successionreportstatus", create_type=False
    )

    for enum_type in (
        device_platform, notification_category, plan_tier, billing_cycle, subscription_status,
        verification_status, stage_status, witness_status, media_type, legacy_release_trigger,
        legacy_note_status, succession_status,
    ):
        enum_type.create(bind, checkfirst=True)

    # ----- New columns on existing tables -----
    op.add_column("identity_users", sa.Column("phone_encrypted", sa.String(length=512), nullable=True))
    op.add_column("identity_users", sa.Column("avatar_url", sa.String(length=512), nullable=True))
    op.add_column(
        "identity_users",
        sa.Column("biometric_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "identity_users",
        sa.Column("language", sa.String(length=16), server_default="en-GB", nullable=False),
    )
    op.add_column(
        "identity_users",
        sa.Column("theme", sa.String(length=16), server_default="dark", nullable=False),
    )
    op.add_column("identity_users", sa.Column("notification_preferences", sa.JSON(), nullable=True))

    op.add_column("identity_user_sessions", sa.Column("public_id", sa.String(length=32), nullable=True))
    op.create_index(
        "ix_identity_user_sessions_public_id", "identity_user_sessions", ["public_id"], unique=True
    )

    op.add_column("vault_documents", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    # ----- Notifications -----
    op.create_table(
        "notification_device_tokens",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("platform", device_platform, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("notification_device_tokens")
    op.create_index(
        "ix_notification_device_tokens_token_hash", "notification_device_tokens", ["token_hash"], unique=True
    )

    op.create_table(
        "notifications",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("category", notification_category, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("notifications")
    op.create_index("ix_notifications_category", "notifications", ["category"])

    # ----- Subscriptions -----
    op.create_table(
        "subscriptions",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("plan", plan_tier, nullable=False),
        sa.Column("billing_cycle", billing_cycle, nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("subscriptions")
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])

    op.create_table(
        "billing_records",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("plan", plan_tier, nullable=False),
        sa.Column("billing_cycle", billing_cycle, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("billing_records")

    # ----- Verification -----
    op.create_table(
        "death_verifications",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("status", verification_status, nullable=False),
        sa.Column("certificate_file_name", sa.String(length=255), nullable=True),
        sa.Column("certificate_object_encrypted", sa.Text(), nullable=True),
        sa.Column("certificate_checksum", sa.String(length=128), nullable=True),
        sa.Column("document_integrity_status", stage_status, nullable=False),
        sa.Column("court_crosscheck_status", stage_status, nullable=False),
        sa.Column("vault_unlock_status", stage_status, nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("death_verifications")
    op.create_index("ix_death_verifications_status", "death_verifications", ["status"])

    op.create_table(
        "verification_witnesses",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("verification_id", _uuid(), nullable=False),
        sa.Column("full_name_encrypted", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("status", witness_status, nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["verification_id"], ["death_verifications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_witnesses_is_deleted", "verification_witnesses", ["is_deleted"])
    op.create_index("ix_verification_witnesses_verification_id", "verification_witnesses", ["verification_id"])
    op.create_index("ix_verification_witnesses_email", "verification_witnesses", ["email"])
    op.create_index(
        "ix_verification_witnesses_public_id", "verification_witnesses", ["public_id"], unique=True
    )

    # ----- Legacy / Memory Vault -----
    op.create_table(
        "legacy_notes",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("title_encrypted", sa.Text(), nullable=False),
        sa.Column("body_encrypted", sa.Text(), nullable=False),
        sa.Column("media_type", media_type, nullable=False),
        sa.Column("media_object_encrypted", sa.Text(), nullable=True),
        sa.Column("status", legacy_note_status, nullable=False),
        sa.Column("release_trigger", legacy_release_trigger, nullable=True),
        sa.Column("release_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("beneficiary_id", _uuid(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("legacy_notes")
    op.create_index("ix_legacy_notes_media_type", "legacy_notes", ["media_type"])

    op.create_table(
        "legacy_memories",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column("storage_object_encrypted", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("legacy_memories")

    # ----- Succession Reports -----
    op.create_table(
        "succession_reports",
        sa.Column("id", _uuid(), nullable=False),
        _public_id(),
        *_timestamps(),
        *_audit_soft_delete(),
        sa.Column("owner_id", _uuid(), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", succession_status, nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("final_message_encrypted", sa.Text(), nullable=True),
        sa.Column("share_token", sa.String(length=64), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["identity_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _std_indexes("succession_reports")
    op.create_index("ix_succession_reports_reference", "succession_reports", ["reference"], unique=True)
    op.create_index("ix_succession_reports_share_token", "succession_reports", ["share_token"])

    # ----- Extend the auditaction enum (Postgres only; SQLite stores enums as VARCHAR) -----
    if bind.dialect.name == "postgresql":
        for value in _NEW_AUDIT_ACTIONS:
            op.execute(f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    op.drop_table("succession_reports")
    op.drop_table("legacy_memories")
    op.drop_table("legacy_notes")
    op.drop_table("verification_witnesses")
    op.drop_table("death_verifications")
    op.drop_table("billing_records")
    op.drop_table("subscriptions")
    op.drop_table("notifications")
    op.drop_table("notification_device_tokens")

    op.drop_column("vault_documents", "expires_at")
    op.drop_index("ix_identity_user_sessions_public_id", table_name="identity_user_sessions")
    op.drop_column("identity_user_sessions", "public_id")
    op.drop_column("identity_users", "notification_preferences")
    op.drop_column("identity_users", "theme")
    op.drop_column("identity_users", "language")
    op.drop_column("identity_users", "biometric_enabled")
    op.drop_column("identity_users", "avatar_url")
    op.drop_column("identity_users", "phone_encrypted")

    for enum_name in (
        "successionreportstatus",
        "legacynotestatus",
        "legacyreleasetrigger",
        "mediatype",
        "witnessstatus",
        "stagestatus",
        "verificationstatus",
        "subscriptionstatus",
        "billingcycle",
        "plantier",
        "notificationcategory",
        "deviceplatform",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)

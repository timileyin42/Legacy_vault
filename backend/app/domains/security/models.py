import enum
import uuid

from sqlalchemy import Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class AuditAction(str, enum.Enum):
    user_registered = "user_registered"
    user_login = "user_login"
    user_logout = "user_logout"
    profile_updated = "profile_updated"
    security_settings_changed = "security_settings_changed"
    session_revoked = "session_revoked"
    device_registered = "device_registered"
    vault_item_created = "vault_item_created"
    vault_item_viewed = "vault_item_viewed"
    vault_item_updated = "vault_item_updated"
    vault_item_deleted = "vault_item_deleted"
    asset_updated = "asset_updated"
    asset_deleted = "asset_deleted"
    document_deleted = "document_deleted"
    beneficiary_created = "beneficiary_created"
    beneficiary_updated = "beneficiary_updated"
    beneficiary_deleted = "beneficiary_deleted"
    trusted_contact_created = "trusted_contact_created"
    inheritance_rule_updated = "inheritance_rule_updated"
    access_request_created = "access_request_created"
    access_request_status_changed = "access_request_status_changed"
    legacy_note_created = "legacy_note_created"
    subscription_changed = "subscription_changed"
    death_verification_submitted = "death_verification_submitted"
    succession_report_generated = "succession_report_generated"


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "security_audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("identity_users.id"), nullable=True, index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_public_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


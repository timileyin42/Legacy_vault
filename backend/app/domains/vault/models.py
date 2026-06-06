import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class VaultCategory(str, enum.Enum):
    bank_account = "bank_account"
    investment = "investment"
    crypto_wallet = "crypto_wallet"
    insurance_policy = "insurance_policy"
    property_record = "property_record"
    business_ownership = "business_ownership"
    subscription = "subscription"
    intellectual_property = "intellectual_property"
    social_media = "social_media"
    personal_note = "personal_note"
    family_record = "family_record"
    password = "password"
    legal_document = "legal_document"


class SecurityLevel(str, enum.Enum):
    standard = "standard"
    high = "high"
    critical = "critical"


class VaultItem(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "vault_items"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    category: Mapped[VaultCategory] = mapped_column(Enum(VaultCategory), index=True)
    title_encrypted: Mapped[str] = mapped_column(Text)
    payload_encrypted: Mapped[str] = mapped_column(Text)
    masked_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    security_level: Mapped[SecurityLevel] = mapped_column(Enum(SecurityLevel), default=SecurityLevel.high)
    release_policy: Mapped[dict] = mapped_column(JSON, default=dict)


class Asset(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "vault_assets"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    vault_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vault_items.id"), nullable=True)
    category: Mapped[VaultCategory] = mapped_column(Enum(VaultCategory), index=True)
    name_encrypted: Mapped[str] = mapped_column(Text)
    value_estimate: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    metadata_encrypted: Mapped[str] = mapped_column(Text)


class Document(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "vault_documents"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    title_encrypted: Mapped[str] = mapped_column(Text)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(80), default="cloudflare_r2")
    storage_object_encrypted: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(128))
    classification: Mapped[str | None] = mapped_column(String(80), nullable=True)
    integrity_status: Mapped[str] = mapped_column(String(40), default="verified")
    notarization_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ocr_text_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_count: Mapped[int] = mapped_column(default=1)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

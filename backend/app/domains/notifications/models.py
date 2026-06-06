import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class DevicePlatform(str, enum.Enum):
    ios = "ios"
    android = "android"
    web = "web"


class NotificationCategory(str, enum.Enum):
    security_alert = "security_alert"
    inheritance_event = "inheritance_event"
    access_request = "access_request"
    document = "document"
    system = "system"


class DeviceToken(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "notification_device_tokens"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    token_encrypted: Mapped[str] = mapped_column(Text)
    platform: Mapped[DevicePlatform] = mapped_column(Enum(DevicePlatform), default=DevicePlatform.ios)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class Notification(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "notifications"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory), default=NotificationCategory.system, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

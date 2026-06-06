import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SuccessionReportStatus(str, enum.Enum):
    draft = "draft"
    verified_released = "verified_released"


class SuccessionReport(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "succession_reports"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[SuccessionReportStatus] = mapped_column(
        Enum(SuccessionReportStatus), default=SuccessionReportStatus.draft
    )
    content_hash: Mapped[str] = mapped_column(String(128))
    final_message_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MediaType(str, enum.Enum):
    written = "written"
    audio = "audio"
    video = "video"


class LegacyReleaseTrigger(str, enum.Enum):
    specific_date = "specific_date"
    proof_of_death = "proof_of_death"
    anniversary = "anniversary"
    event = "event"


class LegacyNoteStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"


class LegacyNote(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "legacy_notes"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    title_encrypted: Mapped[str] = mapped_column(Text)
    body_encrypted: Mapped[str] = mapped_column(Text)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), default=MediaType.written, index=True)
    media_object_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LegacyNoteStatus] = mapped_column(Enum(LegacyNoteStatus), default=LegacyNoteStatus.draft)
    release_trigger: Mapped[LegacyReleaseTrigger | None] = mapped_column(Enum(LegacyReleaseTrigger), nullable=True)
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    beneficiary_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("beneficiaries.id"), nullable=True)


class LegacyMemory(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "legacy_memories"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_object_encrypted: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)

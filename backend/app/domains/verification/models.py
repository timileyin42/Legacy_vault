import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class VerificationStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    rejected = "rejected"


class StageStatus(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    failed = "failed"


class WitnessStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    declined = "declined"


class DeathVerification(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "death_verifications"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.in_progress, index=True
    )
    certificate_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_object_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_integrity_status: Mapped[StageStatus] = mapped_column(Enum(StageStatus), default=StageStatus.pending)
    court_crosscheck_status: Mapped[StageStatus] = mapped_column(Enum(StageStatus), default=StageStatus.pending)
    vault_unlock_status: Mapped[StageStatus] = mapped_column(Enum(StageStatus), default=StageStatus.pending)


class Witness(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "verification_witnesses"

    verification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("death_verifications.id"), index=True)
    full_name_encrypted: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[WitnessStatus] = mapped_column(Enum(WitnessStatus), default=WitnessStatus.pending)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

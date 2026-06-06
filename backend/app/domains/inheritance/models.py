import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ReleaseTrigger(str, enum.Enum):
    death_verification = "death_verification"
    incapacity_verification = "incapacity_verification"
    age_reached = "age_reached"
    scheduled_date = "scheduled_date"
    manual_release = "manual_release"


class AccessRequestStatus(str, enum.Enum):
    submitted = "submitted"
    identity_verification = "identity_verification"
    evidence_review = "evidence_review"
    waiting_period = "waiting_period"
    approved = "approved"
    rejected = "rejected"
    released = "released"


class InheritanceRule(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "inheritance_rules"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id"), index=True)
    vault_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vault_items.id"), nullable=True)
    trigger: Mapped[ReleaseTrigger] = mapped_column(Enum(ReleaseTrigger), index=True)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    instructions_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(default=True)


class AccessRequest(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "access_requests"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id"), index=True)
    request_type: Mapped[ReleaseTrigger] = mapped_column(Enum(ReleaseTrigger), index=True)
    status: Mapped[AccessRequestStatus] = mapped_column(
        Enum(AccessRequestStatus), default=AccessRequestStatus.submitted, index=True
    )
    evidence_summary_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    waiting_period_days: Mapped[int] = mapped_column(default=14)
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[int] = mapped_column(default=50)


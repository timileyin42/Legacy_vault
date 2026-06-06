import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BeneficiaryStatus(str, enum.Enum):
    pending_verification = "pending_verification"
    verified = "verified"
    suspended = "suspended"


class Beneficiary(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "beneficiaries"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    full_name_encrypted: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(255), index=True)
    relationship: Mapped[str] = mapped_column(String(80))
    status: Mapped[BeneficiaryStatus] = mapped_column(
        Enum(BeneficiaryStatus), default=BeneficiaryStatus.pending_verification
    )
    allocation_percent: Mapped[int] = mapped_column(default=0)
    instructions_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)


class TrustedContact(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "trusted_contacts"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    full_name_encrypted: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_weight: Mapped[int] = mapped_column(default=1)


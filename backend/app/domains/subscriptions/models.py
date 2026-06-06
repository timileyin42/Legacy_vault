import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base
from backend.app.shared.models import AuditMixin, ExternalIdMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PlanTier(str, enum.Enum):
    free = "free"
    premium = "premium"
    family = "family"


class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    canceled = "canceled"


class Subscription(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "subscriptions"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    plan: Mapped[PlanTier] = mapped_column(Enum(PlanTier), default=PlanTier.free)
    billing_cycle: Mapped[BillingCycle] = mapped_column(Enum(BillingCycle), default=BillingCycle.monthly)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.active, index=True
    )
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BillingRecord(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "billing_records"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    plan: Mapped[PlanTier] = mapped_column(Enum(PlanTier))
    billing_cycle: Mapped[BillingCycle] = mapped_column(Enum(BillingCycle))
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(40), default="paid")


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    abandoned = "abandoned"


class PaymentTransaction(UUIDPrimaryKeyMixin, ExternalIdMixin, TimestampMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "payment_transactions"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("identity_users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="paystack")
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    plan: Mapped[PlanTier] = mapped_column(Enum(PlanTier))
    billing_cycle: Mapped[BillingCycle] = mapped_column(Enum(BillingCycle))
    amount_minor: Mapped[int] = mapped_column(default=0)  # smallest currency unit (kobo/cents)
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, index=True)
    access_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

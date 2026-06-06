from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.domains.identity.models import User
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.domains.subscriptions.catalog import PLAN_CATALOG
from backend.app.domains.subscriptions.models import (
    BillingCycle,
    BillingRecord,
    PlanTier,
    Subscription,
    SubscriptionStatus,
)
from backend.app.domains.subscriptions.repository import SubscriptionRepository
from backend.app.domains.subscriptions.schemas import (
    BillingRecordResponse,
    ChangePlanRequest,
    PlanResponse,
    SubscriptionResponse,
)


class SubscriptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SubscriptionRepository(db)
        self.audit = AuditRepository(db)

    @staticmethod
    def plans() -> list[PlanResponse]:
        return [
            PlanResponse(
                tier=tier,
                name=plan["name"],
                monthly_price=plan["monthly_price"],
                yearly_price=plan["yearly_price"],
                beneficiary_limit=plan["beneficiary_limit"],
                storage_gb=plan["storage_gb"],
                features=plan["features"],
                recommended=plan.get("recommended", False),
            )
            for tier, plan in PLAN_CATALOG.items()
        ]

    def get_or_create(self, owner: User) -> Subscription:
        return self._get_or_create_by_id(owner.id)

    def _get_or_create_by_id(self, owner_id) -> Subscription:
        subscription = self.repository.get_for_owner(owner_id)
        if subscription is None:
            subscription = Subscription(
                owner_id=owner_id,
                plan=PlanTier.free,
                billing_cycle=BillingCycle.monthly,
                status=SubscriptionStatus.active,
                created_by=owner_id,
                updated_by=owner_id,
            )
            self.repository.create(subscription)
            self.db.flush()
        return subscription

    def activate_paid_plan(
        self, *, owner_id, plan: PlanTier, cycle: BillingCycle, amount_major: float, currency: str
    ) -> Subscription:
        """Apply a paid plan after a confirmed payment. Used by the Paystack finalize path.

        Keyed by owner_id so it can run from the webhook (no authenticated user).
        """
        subscription = self._get_or_create_by_id(owner_id)
        subscription.plan = plan
        subscription.billing_cycle = cycle
        subscription.status = SubscriptionStatus.active
        subscription.renews_at = datetime.now(UTC) + timedelta(days=365 if cycle == BillingCycle.yearly else 30)
        subscription.updated_by = owner_id
        self.repository.add_billing_record(
            BillingRecord(
                owner_id=owner_id,
                description=f"{PLAN_CATALOG[plan]['name']} plan ({cycle.value})",
                plan=plan,
                billing_cycle=cycle,
                amount=amount_major,
                currency=currency,
                status="paid",
                created_by=owner_id,
                updated_by=owner_id,
            )
        )
        self.audit.record(
            action=AuditAction.subscription_changed,
            actor_id=owner_id,
            resource_type="subscription",
            resource_public_id=subscription.public_id,
            metadata_json={"plan": plan.value, "cycle": cycle.value, "paid": True},
        )
        self.db.flush()
        return subscription

    def current(self, owner: User) -> SubscriptionResponse:
        return self._to_response(self.get_or_create(owner))

    def beneficiary_limit(self, owner: User) -> int | None:
        subscription = self.repository.get_for_owner(owner.id)
        plan = subscription.plan if subscription else PlanTier.free
        return PLAN_CATALOG[plan]["beneficiary_limit"]

    def change_plan(self, owner: User, request: ChangePlanRequest) -> SubscriptionResponse:
        subscription = self.get_or_create(owner)
        subscription.plan = request.plan
        subscription.billing_cycle = request.billing_cycle
        subscription.status = SubscriptionStatus.active
        subscription.renews_at = datetime.now(UTC) + timedelta(
            days=365 if request.billing_cycle == BillingCycle.yearly else 30
        )
        subscription.updated_by = owner.id

        plan = PLAN_CATALOG[request.plan]
        amount = plan["yearly_price"] if request.billing_cycle == BillingCycle.yearly else plan["monthly_price"]
        if amount:
            self.repository.add_billing_record(
                BillingRecord(
                    owner_id=owner.id,
                    description=f"{plan['name']} plan ({request.billing_cycle.value})",
                    plan=request.plan,
                    billing_cycle=request.billing_cycle,
                    amount=amount,
                    currency="USD",
                    status="paid",
                    created_by=owner.id,
                    updated_by=owner.id,
                )
            )
        self.audit.record(
            action=AuditAction.subscription_changed,
            actor_id=owner.id,
            resource_type="subscription",
            resource_public_id=subscription.public_id,
            metadata_json={"plan": request.plan.value, "cycle": request.billing_cycle.value},
        )
        self.db.flush()
        return self._to_response(subscription)

    def cancel(self, owner: User) -> SubscriptionResponse:
        subscription = self.get_or_create(owner)
        subscription.status = SubscriptionStatus.canceled
        subscription.updated_by = owner.id
        self.audit.record(
            action=AuditAction.subscription_changed,
            actor_id=owner.id,
            resource_type="subscription",
            resource_public_id=subscription.public_id,
            metadata_json={"status": "canceled"},
        )
        return self._to_response(subscription)

    def billing_history(self, owner: User) -> list[BillingRecordResponse]:
        return [
            BillingRecordResponse(
                id=record.public_id,
                description=record.description,
                plan=record.plan,
                billing_cycle=record.billing_cycle,
                amount=float(record.amount),
                currency=record.currency,
                status=record.status,
                created_at=record.created_at.isoformat(),
            )
            for record in self.repository.list_billing(owner.id)
        ]

    @staticmethod
    def _to_response(subscription: Subscription) -> SubscriptionResponse:
        return SubscriptionResponse(
            id=subscription.public_id,
            plan=subscription.plan,
            billing_cycle=subscription.billing_cycle,
            status=subscription.status.value,
            renews_at=subscription.renews_at.isoformat() if subscription.renews_at else None,
            beneficiary_limit=PLAN_CATALOG[subscription.plan]["beneficiary_limit"],
        )

"""Paystack-backed payment flow for paid subscription plans.

checkout -> Paystack authorization_url; the app pays; confirmation arrives via the
signature-verified webhook (`charge.success`) and/or the app's verify call. Both
paths converge on an idempotent ``_finalize`` that activates the plan once.
"""

import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.domains.identity.models import User
from backend.app.domains.subscriptions.catalog import PLAN_CATALOG
from backend.app.domains.subscriptions.models import (
    BillingCycle,
    PaymentStatus,
    PaymentTransaction,
    PlanTier,
)
from backend.app.domains.subscriptions.repository import SubscriptionRepository
from backend.app.domains.subscriptions.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentVerifyResponse,
)
from backend.app.domains.subscriptions.service import SubscriptionService
from backend.app.integrations.paystack import PaystackClient


def _new_reference() -> str:
    return "lvtx_" + uuid.uuid4().hex


class PaymentService:
    def __init__(self, db: Session, paystack: PaystackClient | None = None) -> None:
        self.db = db
        self.repository = SubscriptionRepository(db)
        self.subscriptions = SubscriptionService(db)
        self.paystack = paystack or PaystackClient()
        self.settings = get_settings()

    def start_checkout(self, owner: User, request: CheckoutRequest) -> CheckoutResponse:
        if request.plan == PlanTier.free:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="The free plan does not require payment."
            )
        catalog = PLAN_CATALOG[request.plan]
        price = catalog["yearly_price"] if request.billing_cycle == BillingCycle.yearly else catalog["monthly_price"]
        if not price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan has no payable amount.")
        amount_minor = int(round(price * 100))
        currency = self.settings.paystack_currency
        reference = _new_reference()

        transaction = PaymentTransaction(
            owner_id=owner.id,
            provider="paystack",
            reference=reference,
            plan=request.plan,
            billing_cycle=request.billing_cycle,
            amount_minor=amount_minor,
            currency=currency,
            status=PaymentStatus.pending,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_transaction(transaction)
        self.db.flush()

        init = self.paystack.initialize_transaction(
            email=owner.email,
            amount_minor=amount_minor,
            reference=reference,
            currency=currency,
            callback_url=self.settings.paystack_callback_url,
            metadata={
                "owner_public_id": owner.public_id,
                "plan": request.plan.value,
                "billing_cycle": request.billing_cycle.value,
                "transaction_id": transaction.public_id,
            },
        )
        transaction.access_code = init.access_code
        self.db.flush()
        return CheckoutResponse(
            authorization_url=init.authorization_url,
            access_code=init.access_code,
            reference=init.reference,
            amount_minor=amount_minor,
            currency=currency,
            public_key=self.settings.paystack_public_key,
        )

    def verify(self, owner: User, reference: str) -> PaymentVerifyResponse:
        transaction = self.repository.get_transaction_for_owner(owner.id, reference)
        if not transaction:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment reference not found.")
        result = self.paystack.verify_transaction(reference)
        if result.paid:
            self._finalize(transaction)
        elif result.status in ("failed", "abandoned"):
            transaction.status = PaymentStatus(result.status)
            self.db.flush()
        return PaymentVerifyResponse(
            reference=reference,
            status=result.status,
            paid=result.paid,
            subscription=self.subscriptions.current(owner),
        )

    def handle_webhook(self, raw_body: bytes, signature: str | None) -> dict:
        if not self.paystack.verify_signature(raw_body, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")
        event = json.loads(raw_body.decode("utf-8"))
        if event.get("event") == "charge.success":
            reference = (event.get("data") or {}).get("reference")
            transaction = self.repository.get_transaction(reference) if reference else None
            if transaction and transaction.status != PaymentStatus.success:
                self._finalize(transaction)
        return {"status": "ok"}

    def finalize_by_reference(self, reference: str) -> bool:
        """Verify a reference against Paystack and finalize if paid (used by the browser callback)."""
        transaction = self.repository.get_transaction(reference)
        if not transaction:
            return False
        result = self.paystack.verify_transaction(reference)
        if result.paid and transaction.status != PaymentStatus.success:
            self._finalize(transaction)
            return True
        return result.paid

    def _finalize(self, transaction: PaymentTransaction) -> None:
        if transaction.status == PaymentStatus.success:
            return
        transaction.status = PaymentStatus.success
        transaction.paid_at = datetime.now(UTC)
        self.subscriptions.activate_paid_plan(
            owner_id=transaction.owner_id,
            plan=transaction.plan,
            cycle=transaction.billing_cycle,
            amount_major=transaction.amount_minor / 100,
            currency=transaction.currency,
        )
        self.db.flush()

from pydantic import BaseModel, Field

from backend.app.domains.subscriptions.models import BillingCycle, PlanTier


class PlanResponse(BaseModel):
    tier: PlanTier
    name: str
    monthly_price: float
    yearly_price: float
    beneficiary_limit: int | None
    storage_gb: int | None
    features: list[str]
    recommended: bool = False


class SubscriptionResponse(BaseModel):
    id: str
    plan: PlanTier
    billing_cycle: BillingCycle
    status: str
    renews_at: str | None
    beneficiary_limit: int | None


class ChangePlanRequest(BaseModel):
    plan: PlanTier
    billing_cycle: BillingCycle = BillingCycle.monthly


class CheckoutRequest(BaseModel):
    plan: PlanTier
    billing_cycle: BillingCycle = BillingCycle.monthly


class CheckoutResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str
    amount_minor: int
    currency: str
    public_key: str | None


class PaymentVerifyResponse(BaseModel):
    reference: str
    status: str
    paid: bool
    subscription: SubscriptionResponse


class BillingRecordResponse(BaseModel):
    id: str
    description: str
    plan: PlanTier
    billing_cycle: BillingCycle
    amount: float
    currency: str
    status: str
    created_at: str

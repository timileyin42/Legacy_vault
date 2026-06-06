from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.subscriptions.models import PlanTier
from backend.app.domains.subscriptions.payment_service import PaymentService
from backend.app.domains.subscriptions.schemas import ChangePlanRequest, CheckoutRequest
from backend.app.domains.subscriptions.service import SubscriptionService
from backend.app.integrations.paystack import PaystackClient, get_paystack_client

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans")
def list_plans():
    plans = SubscriptionService.plans()
    return success_response("Plans retrieved.", [plan.model_dump() for plan in plans])


@router.get("/current")
def current_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = SubscriptionService(db).current(current_user)
    db.commit()
    return success_response("Subscription retrieved.", response.model_dump())


@router.post("/change")
def change_plan(
    request: ChangePlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Paid plans must go through Paystack checkout; /change only handles the free tier.
    if request.plan != PlanTier.free:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /subscriptions/checkout to upgrade to a paid plan.",
        )
    response = SubscriptionService(db).change_plan(current_user, request)
    db.commit()
    return success_response("Subscription updated.", response.model_dump())


@router.post("/cancel")
def cancel_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = SubscriptionService(db).cancel(current_user)
    db.commit()
    return success_response("Subscription canceled.", response.model_dump())


@router.get("/billing-history")
def billing_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = SubscriptionService(db).billing_history(current_user)
    return success_response("Billing history retrieved.", [item.model_dump() for item in response])


# ---- Paystack payment flow ----

@router.post("/checkout")
def checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    paystack: PaystackClient = Depends(get_paystack_client),
    db: Session = Depends(get_db),
):
    response = PaymentService(db, paystack).start_checkout(current_user, request)
    db.commit()
    return success_response("Checkout initialized.", response.model_dump())


@router.get("/checkout/{reference}/verify")
def verify_checkout(
    reference: str,
    current_user: User = Depends(get_current_user),
    paystack: PaystackClient = Depends(get_paystack_client),
    db: Session = Depends(get_db),
):
    response = PaymentService(db, paystack).verify(current_user, reference)
    db.commit()
    return success_response("Payment verification complete.", response.model_dump())


@router.post("/paystack/webhook", include_in_schema=False)
async def paystack_webhook(
    request: Request,
    paystack: PaystackClient = Depends(get_paystack_client),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    result = PaymentService(db, paystack).handle_webhook(raw_body, signature)
    db.commit()
    return result


@router.get("/paystack/callback", include_in_schema=False)
def paystack_callback(
    reference: str | None = None,
    trxref: str | None = None,
    paystack: PaystackClient = Depends(get_paystack_client),
    db: Session = Depends(get_db),
):
    ref = reference or trxref
    paid = False
    if ref:
        paid = PaymentService(db, paystack).finalize_by_reference(ref)
        db.commit()
    headline = "Payment successful" if paid else "Payment received"
    body = (
        "Your subscription is now active. You can return to the LegacyVault app."
        if paid
        else "We're confirming your payment. You can return to the LegacyVault app — your plan will update shortly."
    )
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LegacyVault</title></head>
<body style="margin:0;background:#051424;color:#d4e4fa;font-family:Arial,sans-serif;text-align:center;">
<div style="max-width:480px;margin:80px auto;padding:32px;">
<div style="font-size:48px;">{'✅' if paid else '⏳'}</div>
<h1 style="color:#c3c0ff;">{headline}</h1>
<p style="color:#c7c6cd;line-height:1.6;">{body}</p>
</div></body></html>"""
    return HTMLResponse(content=html)

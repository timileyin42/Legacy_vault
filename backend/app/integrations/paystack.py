"""Paystack payment integration for subscriptions.

Used to charge for paid plan upgrades. The flow (mobile-friendly):

  1. Backend initializes a transaction -> Paystack returns an ``authorization_url``
     + ``access_code`` + ``reference``.
  2. The app opens the authorization_url in a webview (or uses the Paystack mobile
     SDK with the access_code).
  3. Confirmation is taken from the **webhook** (`charge.success`, signature-verified)
     and/or the app calling the backend verify endpoint. Browser callbacks on mobile
     are unreliable, so the webhook is the source of truth.

When ``PAYSTACK_SECRET_KEY`` is not configured the client raises 503 on use
(payments cannot be silently skipped). Inject a fake client in tests.
"""

import hashlib
import hmac
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from backend.app.core.config import Settings, get_settings

PAYSTACK_BASE_URL = "https://api.paystack.co"


@dataclass(frozen=True)
class InitResult:
    authorization_url: str
    access_code: str
    reference: str


@dataclass(frozen=True)
class VerifyResult:
    status: str  # Paystack transaction status: success, failed, abandoned, ...
    reference: str
    amount: int  # minor units (kobo/cents)
    currency: str
    paid: bool
    metadata: dict


class PaystackClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.paystack_secret_key)

    def _require(self) -> str:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payments are not configured."
            )
        return self.settings.paystack_secret_key  # type: ignore[return-value]

    def initialize_transaction(
        self,
        *,
        email: str,
        amount_minor: int,
        reference: str,
        currency: str,
        callback_url: str | None,
        metadata: dict,
    ) -> InitResult:
        secret = self._require()
        payload = {
            "email": email,
            "amount": amount_minor,
            "reference": reference,
            "currency": currency,
            "metadata": metadata,
        }
        if callback_url:
            payload["callback_url"] = callback_url
        response = httpx.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return InitResult(
            authorization_url=data["authorization_url"],
            access_code=data["access_code"],
            reference=data["reference"],
        )

    def verify_transaction(self, reference: str) -> VerifyResult:
        secret = self._require()
        response = httpx.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret}"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()["data"]
        return VerifyResult(
            status=data.get("status", "failed"),
            reference=data.get("reference", reference),
            amount=int(data.get("amount", 0)),
            currency=data.get("currency", self.settings.paystack_currency),
            paid=data.get("status") == "success",
            metadata=data.get("metadata") or {},
        )

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        """Validate a Paystack webhook via the x-paystack-signature header (HMAC-SHA512)."""
        if not signature or not self.is_configured:
            return False
        expected = hmac.new(
            self.settings.paystack_secret_key.encode("utf-8"), raw_body, hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


def get_paystack_client() -> PaystackClient:
    return PaystackClient()

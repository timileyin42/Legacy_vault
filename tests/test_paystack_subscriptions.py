import json

from fastapi.testclient import TestClient

from backend.app.integrations.paystack import InitResult, VerifyResult, get_paystack_client


class FakePaystack:
    """Stand-in for the Paystack API: echoes the reference, reports paid, accepts 'valid-sig'."""

    def __init__(self, paid: bool = True) -> None:
        self.paid = paid

    def initialize_transaction(self, *, email, amount_minor, reference, currency, callback_url, metadata) -> InitResult:
        return InitResult(
            authorization_url=f"https://checkout.paystack.com/{reference}",
            access_code="acc_test_123",
            reference=reference,
        )

    def verify_transaction(self, reference: str) -> VerifyResult:
        return VerifyResult(
            status="success" if self.paid else "failed",
            reference=reference,
            amount=490000,
            currency="NGN",
            paid=self.paid,
            metadata={},
        )

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        return signature == "valid-sig"


def _use_fake(client: TestClient, paid: bool = True) -> FakePaystack:
    fake = FakePaystack(paid=paid)
    client.app.dependency_overrides[get_paystack_client] = lambda: fake
    return fake


def test_checkout_then_verify_upgrades_and_raises_limit(client: TestClient, auth_headers: dict[str, str]):
    _use_fake(client)

    checkout = client.post(
        "/api/v1/subscriptions/checkout",
        headers=auth_headers,
        json={"plan": "premium", "billing_cycle": "monthly"},
    )
    assert checkout.status_code == 200
    data = checkout.json()["data"]
    assert data["authorization_url"].startswith("https://checkout.paystack.com/")
    reference = data["reference"]
    assert data["amount_minor"] == 4900  # 49 * 100, in the configured currency's minor unit

    verify = client.get(f"/api/v1/subscriptions/checkout/{reference}/verify", headers=auth_headers)
    assert verify.status_code == 200
    body = verify.json()["data"]
    assert body["paid"] is True
    assert body["subscription"]["plan"] == "premium"
    assert body["subscription"]["beneficiary_limit"] == 5

    # Premium raises the beneficiary cap from 2 to 5.
    def add(email):
        return client.post(
            "/api/v1/beneficiaries",
            headers=auth_headers,
            json={"full_name": "Heir", "email": email, "relationship": "child"},
        )

    assert add("a@example.com").status_code == 200
    assert add("b@example.com").status_code == 200
    assert add("c@example.com").status_code == 200  # would be 402 on the free tier

    history = client.get("/api/v1/subscriptions/billing-history", headers=auth_headers).json()["data"]
    assert len(history) == 1
    assert history[0]["amount"] == 49.0
    assert history[0]["currency"] == "NGN"


def test_verify_is_idempotent(client: TestClient, auth_headers: dict[str, str]):
    _use_fake(client)
    ref = client.post(
        "/api/v1/subscriptions/checkout", headers=auth_headers, json={"plan": "premium"}
    ).json()["data"]["reference"]
    client.get(f"/api/v1/subscriptions/checkout/{ref}/verify", headers=auth_headers)
    client.get(f"/api/v1/subscriptions/checkout/{ref}/verify", headers=auth_headers)
    # Finalizing twice must not double-charge the billing history.
    history = client.get("/api/v1/subscriptions/billing-history", headers=auth_headers).json()["data"]
    assert len(history) == 1


def test_webhook_finalizes_on_valid_signature(client: TestClient, auth_headers: dict[str, str]):
    _use_fake(client)
    ref = client.post(
        "/api/v1/subscriptions/checkout", headers=auth_headers, json={"plan": "family", "billing_cycle": "yearly"}
    ).json()["data"]["reference"]

    payload = json.dumps({"event": "charge.success", "data": {"reference": ref}}).encode()

    # Bad signature is rejected.
    bad = client.post("/api/v1/subscriptions/paystack/webhook", content=payload, headers={"x-paystack-signature": "nope"})
    assert bad.status_code == 401

    # Valid signature finalizes the subscription.
    ok = client.post(
        "/api/v1/subscriptions/paystack/webhook", content=payload, headers={"x-paystack-signature": "valid-sig"}
    )
    assert ok.status_code == 200
    current = client.get("/api/v1/subscriptions/current", headers=auth_headers).json()["data"]
    assert current["plan"] == "family"


def test_change_endpoint_rejects_paid_plans(client: TestClient, auth_headers: dict[str, str]):
    resp = client.post("/api/v1/subscriptions/change", headers=auth_headers, json={"plan": "premium"})
    assert resp.status_code == 400
    # Free is still allowed via /change.
    free = client.post("/api/v1/subscriptions/change", headers=auth_headers, json={"plan": "free"})
    assert free.status_code == 200

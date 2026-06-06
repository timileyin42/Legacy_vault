from fastapi.testclient import TestClient


def test_plans_listed_with_free_premium_family(client: TestClient):
    response = client.get("/api/v1/subscriptions/plans")
    assert response.status_code == 200
    tiers = {plan["tier"] for plan in response.json()["data"]}
    assert tiers == {"free", "premium", "family"}


def test_current_defaults_to_free(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/subscriptions/current", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["plan"] == "free"
    assert data["beneficiary_limit"] == 2


def test_free_tier_caps_beneficiaries_until_paid_upgrade(client: TestClient, auth_headers: dict[str, str]):
    # Paid upgrades now go through Paystack checkout (see test_paystack_subscriptions.py);
    # here we just confirm the free tier caps at two beneficiaries.
    def add(email: str):
        return client.post(
            "/api/v1/beneficiaries",
            headers=auth_headers,
            json={"full_name": "Heir", "email": email, "relationship": "child"},
        )

    assert add("one@example.com").status_code == 200
    assert add("two@example.com").status_code == 200
    assert add("three@example.com").status_code == 402

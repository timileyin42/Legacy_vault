from fastapi.testclient import TestClient


def test_dashboard_summary_counts_and_readiness(client: TestClient, auth_headers: dict[str, str]):
    client.post(
        "/api/v1/vault/items",
        headers=auth_headers,
        json={"category": "bank_account", "title": "Primary checking"},
    )
    client.post(
        "/api/v1/beneficiaries",
        headers=auth_headers,
        json={"full_name": "Named Heir", "email": "heir@example.com", "relationship": "child"},
    )

    response = client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["vault_items"] == 1
    assert data["beneficiaries"] == 1
    assert data["assets"] == 0
    assert data["access_requests"] == 0
    # readiness = min(100, 20 + vault_items*10 + beneficiaries*20) = 20 + 10 + 20
    assert data["inheritance_readiness_score"] == 50


def test_dashboard_summary_requires_authentication(client: TestClient):
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401
    assert response.json()["success"] is False

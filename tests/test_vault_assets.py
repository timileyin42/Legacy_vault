from fastapi.testclient import TestClient


def test_create_and_list_asset_returns_decrypted_summary(client: TestClient, auth_headers: dict[str, str]):
    create = client.post(
        "/api/v1/vault/assets",
        headers=auth_headers,
        json={
            "category": "investment",
            "name": "Global Equity Trust",
            "value_estimate": 2450000,
            "currency": "usd",
            "metadata": {"account": "8821"},
        },
    )

    assert create.status_code == 200
    created = create.json()["data"]
    assert created["name"] == "Global Equity Trust"
    assert created["value_estimate"] == 2450000.0
    assert created["currency"] == "USD"

    listed = client.get("/api/v1/vault/assets", headers=auth_headers)
    assert listed.status_code == 200
    assets = listed.json()["data"]
    assert [a["name"] for a in assets] == ["Global Equity Trust"]
    # Encrypted metadata must not leak.
    assert "8821" not in listed.text


def test_get_vault_item_by_public_id(client: TestClient, auth_headers: dict[str, str]):
    created = client.post(
        "/api/v1/vault/items",
        headers=auth_headers,
        json={
            "category": "password",
            "title": "Email master password",
            "sensitive_payload": {"password": "top-secret-value"},
        },
    ).json()["data"]

    response = client.get(f"/api/v1/vault/items/{created['id']}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == created["id"]
    assert data["title"] == "Email master password"
    assert "top-secret-value" not in response.text


def test_get_missing_vault_item_returns_404(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/vault/items/lv_missing_item", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["success"] is False

from fastapi.testclient import TestClient


def _create_item(client: TestClient, headers: dict[str, str]) -> dict:
    return client.post(
        "/api/v1/vault/items",
        headers=headers,
        json={"category": "password", "title": "Email login", "sensitive_payload": {"password": "secret"}},
    ).json()["data"]


def _create_asset(client: TestClient, headers: dict[str, str]) -> dict:
    return client.post(
        "/api/v1/vault/assets",
        headers=headers,
        json={"category": "investment", "name": "Equity Trust", "value_estimate": 1000, "currency": "USD"},
    ).json()["data"]


def test_item_update_and_delete(client: TestClient, auth_headers: dict[str, str]):
    item = _create_item(client, auth_headers)
    updated = client.put(
        f"/api/v1/vault/items/{item['id']}",
        headers=auth_headers,
        json={"title": "Renamed login", "masked_hint": "ends 99"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "Renamed login"

    deleted = client.delete(f"/api/v1/vault/items/{item['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/vault/items/{item['id']}", headers=auth_headers).status_code == 404


def test_asset_get_update_delete(client: TestClient, auth_headers: dict[str, str]):
    asset = _create_asset(client, auth_headers)
    got = client.get(f"/api/v1/vault/assets/{asset['id']}", headers=auth_headers)
    assert got.status_code == 200

    updated = client.put(
        f"/api/v1/vault/assets/{asset['id']}",
        headers=auth_headers,
        json={"value_estimate": 5000},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["value_estimate"] == 5000.0

    assert client.delete(f"/api/v1/vault/assets/{asset['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/vault/assets/{asset['id']}", headers=auth_headers).status_code == 404


def test_document_categories_and_expiry(client: TestClient, auth_headers: dict[str, str]):
    client.post(
        "/api/v1/vault/documents",
        headers=auth_headers,
        json={
            "title": "Last Will",
            "document_type": "will",
            "storage_object": "r2://bucket/will.pdf",
            "checksum": "abc123456789def0",
            "expires_at": "2026-07-01T00:00:00Z",
        },
    )
    client.post(
        "/api/v1/vault/documents",
        headers=auth_headers,
        json={
            "title": "Deed",
            "document_type": "deed",
            "storage_object": "r2://bucket/deed.pdf",
            "checksum": "abc123456789def1",
        },
    )

    categories = client.get("/api/v1/vault/documents/categories", headers=auth_headers)
    assert categories.status_code == 200
    cats = {c["category"]: c["count"] for c in categories.json()["data"]}
    assert cats == {"deed": 1, "will": 1}

    expiring = client.get("/api/v1/vault/documents/expiring?within_days=120", headers=auth_headers)
    assert expiring.status_code == 200
    titles = [d["title"] for d in expiring.json()["data"]]
    assert titles == ["Last Will"]

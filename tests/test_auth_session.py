from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "session@example.com") -> dict:
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Session Owner",
            "password": "very-secure-password",
            "device_fingerprint": "ios-device-1",
        },
    ).json()["data"]


def test_refresh_token_issues_new_access_token(client: TestClient):
    tokens = _register(client)["tokens"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]


def test_refresh_rejects_unknown_token(client: TestClient):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-refresh-token-value"},
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_me_returns_current_user(client: TestClient):
    tokens = _register(client)["tokens"]
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "session@example.com"
    assert data["role"] == "user"
    assert data["mfa_enabled"] is False


def test_protected_route_requires_authentication(client: TestClient):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["success"] is False

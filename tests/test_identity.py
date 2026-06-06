from fastapi.testclient import TestClient


def test_register_returns_standard_response_and_tokens(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Ada Person",
            "password": "very-secure-password",
            "device_fingerprint": "iphone-15",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Registration successful."
    assert body["data"]["user"]["email"] == "person@example.com"
    assert body["data"]["tokens"]["token_type"] == "bearer"
    assert "access_token" in body["data"]["tokens"]
    assert "refresh_token" in body["data"]["tokens"]


def test_login_rejects_invalid_password(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "person@example.com",
            "full_name": "Ada Person",
            "password": "very-secure-password",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


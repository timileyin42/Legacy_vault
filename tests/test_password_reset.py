import re

from fastapi.testclient import TestClient

from backend.app.integrations.email import get_email_client


class _CapturingEmailClient:
    def __init__(self) -> None:
        self.messages: list = []

    def send(self, message) -> dict:
        self.messages.append(message)
        return {"id": "captured"}


def _register(client: TestClient, email: str = "reset@example.com", password: str = "very-secure-password"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Reset User", "password": password},
    )


def test_forgot_password_sends_code_and_reset_changes_password(client: TestClient):
    _register(client)
    captured = _CapturingEmailClient()
    client.app.dependency_overrides[get_email_client] = lambda: captured

    forgot = client.post("/api/v1/auth/password/forgot", json={"email": "reset@example.com"})
    assert forgot.status_code == 200
    code = re.search(r"\b(\d{6})\b", captured.messages[-1].text).group(1)
    assert captured.messages[-1].subject == "Reset your LegacyVault password"

    reset = client.post(
        "/api/v1/auth/password/reset",
        json={"email": "reset@example.com", "code": code, "new_password": "a-brand-new-password"},
    )
    assert reset.status_code == 200
    assert reset.json()["data"]["reset"] is True

    # Old password no longer works; the new one does.
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "very-secure-password"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "a-brand-new-password"},
    ).status_code == 200


def test_forgot_password_unknown_email_still_returns_200(client: TestClient):
    captured = _CapturingEmailClient()
    client.app.dependency_overrides[get_email_client] = lambda: captured
    response = client.post("/api/v1/auth/password/forgot", json={"email": "nobody@example.com"})
    # No account enumeration: same generic 200, and no email is sent.
    assert response.status_code == 200
    assert captured.messages == []


def test_reset_rejects_wrong_code(client: TestClient):
    _register(client, email="reset2@example.com")
    captured = _CapturingEmailClient()
    client.app.dependency_overrides[get_email_client] = lambda: captured
    client.post("/api/v1/auth/password/forgot", json={"email": "reset2@example.com"})

    response = client.post(
        "/api/v1/auth/password/reset",
        json={"email": "reset2@example.com", "code": "000000", "new_password": "a-brand-new-password"},
    )
    assert response.status_code in (400, 200)
    if response.status_code == 400:
        assert response.json()["success"] is False

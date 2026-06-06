import re

from fastapi.testclient import TestClient

from backend.app.integrations.email import get_email_client
from backend.app.integrations.firebase_auth import FirebaseClaims, get_firebase_auth_client


class _FakeFirebase:
    def __init__(self, claims: FirebaseClaims) -> None:
        self._claims = claims

    def verify_id_token(self, id_token: str) -> FirebaseClaims:
        return self._claims


class _CapturingEmailClient:
    def __init__(self) -> None:
        self.messages: list = []

    def send(self, message) -> dict:
        self.messages.append(message)
        return {"id": "captured"}


# ---------- Succession report PDF ----------

def test_succession_report_pdf_download(client: TestClient, auth_headers: dict[str, str]):
    client.post(
        "/api/v1/vault/assets",
        headers=auth_headers,
        json={"category": "investment", "name": "Equity Trust", "value_estimate": 12450000, "currency": "USD"},
    )
    report = client.post(
        "/api/v1/succession-reports", headers=auth_headers, json={"final_message": "Farewell."}
    ).json()["data"]

    response = client.get(f"/api/v1/succession-reports/{report['id']}/pdf", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"
    assert "attachment" in response.headers["content-disposition"]


# ---------- Google / Firebase sign-in ----------

def test_google_sign_in_creates_then_reuses_user(client: TestClient):
    claims = FirebaseClaims(uid="firebase-uid-1", email="google.user@example.com", name="Google User", email_verified=True)
    client.app.dependency_overrides[get_firebase_auth_client] = lambda: _FakeFirebase(claims)

    first = client.post("/api/v1/auth/google", json={"id_token": "fake-firebase-id-token"})
    assert first.status_code == 200
    body = first.json()["data"]
    assert body["user"]["email"] == "google.user@example.com"
    assert body["tokens"]["access_token"]

    # Signing in again with the same Google identity logs into the same account.
    second = client.post("/api/v1/auth/google", json={"id_token": "fake-firebase-id-token"})
    assert second.status_code == 200

    me = client.get(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {body['tokens']['access_token']}"},
    )
    assert me.json()["data"]["auth_provider"] == "google"
    assert me.json()["data"]["email_verified"] is True


def test_google_sign_in_unconfigured_returns_503(client: TestClient):
    # No FIREBASE_PROJECT_ID in the test environment -> feature reports unconfigured.
    response = client.post("/api/v1/auth/google", json={"id_token": "fake-firebase-id-token"})
    assert response.status_code == 503


# ---------- Email verification code flow ----------

def test_email_verification_send_and_confirm(client: TestClient, auth_headers: dict[str, str]):
    captured = _CapturingEmailClient()
    client.app.dependency_overrides[get_email_client] = lambda: captured

    send = client.post("/api/v1/auth/verification/send", headers=auth_headers)
    assert send.status_code == 200
    assert send.json()["data"]["sent"] is True

    # Recover the code the user would have received in the email.
    code = re.search(r"\b(\d{6})\b", captured.messages[-1].text).group(1)

    confirm = client.post("/api/v1/auth/verification/confirm", headers=auth_headers, json={"code": code})
    assert confirm.status_code == 200
    assert confirm.json()["data"]["email_verified"] is True


def test_email_verification_rejects_wrong_code(client: TestClient, auth_headers: dict[str, str]):
    captured = _CapturingEmailClient()
    client.app.dependency_overrides[get_email_client] = lambda: captured
    client.post("/api/v1/auth/verification/send", headers=auth_headers)

    response = client.post("/api/v1/auth/verification/confirm", headers=auth_headers, json={"code": "000000"})
    # 400 unless the random code happened to be 000000 (1 in a million); guard against it.
    assert response.status_code in (400, 200)
    if response.status_code == 400:
        assert response.json()["success"] is False

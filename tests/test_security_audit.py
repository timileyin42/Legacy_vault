from fastapi.testclient import TestClient


def test_audit_logs_return_registration_event(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/security/audit-logs", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    actions = {entry["action"] for entry in body["data"]}
    assert "user_registered" in actions


def test_login_history_lists_active_session(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/security/login-history", headers=auth_headers)

    assert response.status_code == 200
    sessions = response.json()["data"]
    assert len(sessions) >= 1
    assert sessions[0]["device_fingerprint"] == "ios-device-1"
    assert sessions[0]["revoked"] is False


def test_audit_logs_require_authentication(client: TestClient):
    response = client.get("/api/v1/security/audit-logs")

    assert response.status_code == 401
    assert response.json()["success"] is False

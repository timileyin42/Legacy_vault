from fastapi.testclient import TestClient


def test_get_and_update_profile(client: TestClient, auth_headers: dict[str, str]):
    initial = client.get("/api/v1/auth/profile", headers=auth_headers)
    assert initial.status_code == 200
    assert initial.json()["data"]["theme"] == "dark"

    response = client.put(
        "/api/v1/auth/profile",
        headers=auth_headers,
        json={"full_name": "Julian Sterling", "phone": "+41 79 123 45 67", "theme": "light"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["full_name"] == "Julian Sterling"
    assert data["phone"] == "+41 79 123 45 67"
    assert data["theme"] == "light"
    # Phone is encrypted at rest and must not leak via any other surface.
    assert "+41 79 123 45 67" in response.text  # returned to its owner only


def test_update_notification_and_security_settings(client: TestClient, auth_headers: dict[str, str]):
    notif = client.put(
        "/api/v1/auth/notification-settings",
        headers=auth_headers,
        json={"product_updates": True, "security_logs": False},
    )
    assert notif.status_code == 200
    prefs = notif.json()["data"]["notification_preferences"]
    assert prefs["product_updates"] is True
    assert prefs["security_logs"] is False

    sec = client.put(
        "/api/v1/auth/security-settings",
        headers=auth_headers,
        json={"biometric_enabled": True},
    )
    assert sec.status_code == 200
    assert sec.json()["data"]["biometric_enabled"] is True


def test_sessions_list_and_revoke(client: TestClient, auth_headers: dict[str, str]):
    sessions = client.get("/api/v1/auth/sessions", headers=auth_headers).json()["data"]
    assert len(sessions) >= 1
    session_id = sessions[0]["id"]

    revoke = client.post(f"/api/v1/auth/sessions/{session_id}/revoke", headers=auth_headers)
    assert revoke.status_code == 200
    assert revoke.json()["data"]["revoked"] is True


def test_logout_and_export(client: TestClient, auth_headers: dict[str, str]):
    client.post(
        "/api/v1/vault/assets",
        headers=auth_headers,
        json={"category": "investment", "name": "Trust Fund", "value_estimate": 100},
    )
    export = client.post("/api/v1/auth/export", headers=auth_headers)
    assert export.status_code == 200
    data = export.json()["data"]
    assert data["counts"]["assets"] == 1
    assert data["assets"][0]["name"] == "Trust Fund"

    logout = client.post("/api/v1/auth/logout", headers=auth_headers, json={})
    assert logout.status_code == 200
    assert logout.json()["data"]["revoked_sessions"] >= 1

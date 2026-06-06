from fastapi.testclient import TestClient


def test_register_device_and_list(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/v1/notifications/devices",
        headers=auth_headers,
        json={"token": "fcm-registration-token-abcdef123456", "platform": "ios"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["platform"] == "ios"
    # Raw FCM token must never be echoed back.
    assert "fcm-registration-token-abcdef123456" not in response.text

    devices = client.get("/api/v1/notifications/devices", headers=auth_headers)
    assert devices.status_code == 200
    assert len(devices.json()["data"]) == 1


def test_registering_same_token_is_idempotent(client: TestClient, auth_headers: dict[str, str]):
    payload = {"token": "fcm-registration-token-abcdef123456", "platform": "ios"}
    client.post("/api/v1/notifications/devices", headers=auth_headers, json=payload)
    client.post("/api/v1/notifications/devices", headers=auth_headers, json=payload)
    devices = client.get("/api/v1/notifications/devices", headers=auth_headers).json()["data"]
    assert len(devices) == 1


def test_notifications_feed_starts_empty(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/notifications", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] == {"unread_count": 0, "items": []}

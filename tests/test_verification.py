from fastapi.testclient import TestClient


def test_death_verification_lifecycle_and_notification(client: TestClient, auth_headers: dict[str, str]):
    create = client.post(
        "/api/v1/verification/death",
        headers=auth_headers,
        json={
            "certificate_file_name": "DC_Final.pdf",
            "certificate_object": "r2://bucket/death-cert.pdf",
            "certificate_checksum": "abc123456789def0",
            "witnesses": [
                {"full_name": "Sarah Jenkins", "email": "sarah@example.com"},
                {"full_name": "Marcus Thorne", "email": "marcus@example.com"},
            ],
        },
    )
    assert create.status_code == 200
    data = create.json()["data"]
    assert data["certificate_uploaded"] is True
    assert data["document_integrity_status"] == "validated"
    assert data["progress_percent"] == 33
    assert len(data["witnesses"]) == 2
    # Certificate object reference is encrypted and never returned.
    assert "r2://bucket/death-cert.pdf" not in create.text

    verification_id = data["id"]
    witness_id = data["witnesses"][0]["id"]

    respond = client.post(
        f"/api/v1/verification/death/{verification_id}/witnesses/{witness_id}/respond",
        headers=auth_headers,
        json={"status": "verified"},
    )
    assert respond.status_code == 200
    assert respond.json()["data"]["witness_consensus"] == "1 of 2"

    stages = client.patch(
        f"/api/v1/verification/death/{verification_id}/stages",
        headers=auth_headers,
        json={"court_crosscheck_status": "validated", "vault_unlock_status": "validated"},
    )
    assert stages.status_code == 200
    assert stages.json()["data"]["progress_percent"] == 100
    assert stages.json()["data"]["status"] == "completed"

    # Submitting a death verification raises an in-app notification (the FCM path).
    feed = client.get("/api/v1/notifications", headers=auth_headers).json()["data"]
    assert feed["unread_count"] >= 1
    assert any(item["category"] == "inheritance_event" for item in feed["items"])


def test_emergency_access_status(client: TestClient, auth_headers: dict[str, str]):
    empty = client.get("/api/v1/verification/emergency-access", headers=auth_headers)
    assert empty.status_code == 200
    assert empty.json()["data"]["has_active_verification"] is False

    client.post("/api/v1/verification/death", headers=auth_headers, json={})
    status = client.get("/api/v1/verification/emergency-access", headers=auth_headers)
    assert status.json()["data"]["has_active_verification"] is True
    assert status.json()["data"]["waiting_period_days"] == 14

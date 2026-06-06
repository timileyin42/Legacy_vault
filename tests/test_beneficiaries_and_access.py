from fastapi.testclient import TestClient


def _create_beneficiary(client: TestClient, headers: dict[str, str], email: str):
    return client.post(
        "/api/v1/beneficiaries",
        headers=headers,
        json={
            "full_name": "Named Heir",
            "email": email,
            "relationship": "child",
            "allocation_percent": 50,
            "instructions": "Release only after verified event.",
        },
    )


def test_free_tier_limits_beneficiaries(client: TestClient, auth_headers: dict[str, str]):
    assert _create_beneficiary(client, auth_headers, "one@example.com").status_code == 200
    assert _create_beneficiary(client, auth_headers, "two@example.com").status_code == 200

    response = _create_beneficiary(client, auth_headers, "three@example.com")

    assert response.status_code == 402
    assert response.json()["success"] is False


def test_access_request_moves_to_waiting_period(client: TestClient, auth_headers: dict[str, str]):
    beneficiary = _create_beneficiary(client, auth_headers, "heir@example.com").json()["data"]
    create_response = client.post(
        "/api/v1/inheritance/access-requests",
        headers=auth_headers,
        json={
            "beneficiary_id": beneficiary["id"],
            "request_type": "death_verification",
            "evidence_summary": "Death certificate submitted for review.",
        },
    )
    assert create_response.status_code == 200
    access_request = create_response.json()["data"]
    assert access_request["status"] == "identity_verification"

    update_response = client.patch(
        f"/api/v1/inheritance/access-requests/{access_request['id']}/status",
        headers=auth_headers,
        json={"status": "waiting_period", "reviewer_notes": "Evidence accepted."},
    )

    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["status"] == "waiting_period"
    assert updated["release_at"] is not None


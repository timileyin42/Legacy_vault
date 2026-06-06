from fastapi.testclient import TestClient


def _create(client: TestClient, headers: dict[str, str], email: str, allocation: int = 0) -> dict:
    return client.post(
        "/api/v1/beneficiaries",
        headers=headers,
        json={
            "full_name": "Named Heir",
            "email": email,
            "relationship": "child",
            "allocation_percent": allocation,
        },
    ).json()["data"]


def test_get_update_delete_beneficiary(client: TestClient, auth_headers: dict[str, str]):
    created = _create(client, auth_headers, "heir@example.com", allocation=40)

    got = client.get(f"/api/v1/beneficiaries/{created['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["data"]["allocation_percent"] == 40

    updated = client.put(
        f"/api/v1/beneficiaries/{created['id']}",
        headers=auth_headers,
        json={"allocation_percent": 65, "relationship": "spouse"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["allocation_percent"] == 65
    assert updated.json()["data"]["relationship"] == "spouse"

    deleted = client.delete(f"/api/v1/beneficiaries/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/beneficiaries/{created['id']}", headers=auth_headers).status_code == 404


def test_verify_and_allocation_summary(client: TestClient, auth_headers: dict[str, str]):
    a = _create(client, auth_headers, "a@example.com", allocation=60)
    _create(client, auth_headers, "b@example.com", allocation=40)

    verify = client.post(f"/api/v1/beneficiaries/{a['id']}/verify", headers=auth_headers, json={})
    assert verify.status_code == 200
    assert verify.json()["data"]["status"] == "verified"

    summary = client.get("/api/v1/beneficiaries/summary", headers=auth_headers)
    assert summary.status_code == 200
    data = summary.json()["data"]
    assert data["beneficiary_count"] == 2
    assert data["total_allocated_percent"] == 100
    assert data["fully_allocated"] is True


def test_trusted_contacts_crud(client: TestClient, auth_headers: dict[str, str]):
    create = client.post(
        "/api/v1/trusted-contacts",
        headers=auth_headers,
        json={"full_name": "Robert Sterling", "email": "robert@example.com", "phone": "+1 555 0100"},
    )
    assert create.status_code == 200
    assert create.json()["data"]["full_name"] == "Robert Sterling"

    listed = client.get("/api/v1/trusted-contacts", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1

from fastapi.testclient import TestClient


def _beneficiary(client: TestClient, headers: dict[str, str], email: str, allocation: int) -> dict:
    return client.post(
        "/api/v1/beneficiaries",
        headers=headers,
        json={"full_name": "Heir", "email": email, "relationship": "child", "allocation_percent": allocation},
    ).json()["data"]


def _rule(client: TestClient, headers: dict[str, str], beneficiary_id: str) -> dict:
    return client.post(
        "/api/v1/inheritance/rules",
        headers=headers,
        json={"beneficiary_id": beneficiary_id, "trigger": "death_verification"},
    ).json()["data"]


def test_list_get_update_toggle_rule(client: TestClient, auth_headers: dict[str, str]):
    beneficiary = _beneficiary(client, auth_headers, "heir@example.com", 50)
    rule = _rule(client, auth_headers, beneficiary["id"])

    listed = client.get("/api/v1/inheritance/rules", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1

    got = client.get(f"/api/v1/inheritance/rules/{rule['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["data"]["beneficiary_id"] == beneficiary["id"]

    updated = client.put(
        f"/api/v1/inheritance/rules/{rule['id']}",
        headers=auth_headers,
        json={"trigger": "age_reached", "conditions": {"age": 25}},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["trigger"] == "age_reached"

    toggled = client.post(
        f"/api/v1/inheritance/rules/{rule['id']}/toggle",
        headers=auth_headers,
        json={"active": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["data"]["active"] is False


def test_distribution_summary(client: TestClient, auth_headers: dict[str, str]):
    a = _beneficiary(client, auth_headers, "a@example.com", 60)
    _rule(client, auth_headers, a["id"])
    _beneficiary(client, auth_headers, "b@example.com", 40)

    summary = client.get("/api/v1/inheritance/rules/distribution-summary", headers=auth_headers)
    assert summary.status_code == 200
    data = summary.json()["data"]
    assert data["total_allocated_percent"] == 100
    assert data["unallocated_percent"] == 0
    assert data["active_rule_count"] == 1
    assert data["engine_status"] == "optimal"
    assert len(data["entries"]) == 2

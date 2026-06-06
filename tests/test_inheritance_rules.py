from fastapi.testclient import TestClient


def _create_beneficiary(client: TestClient, headers: dict[str, str]) -> dict:
    return client.post(
        "/api/v1/beneficiaries",
        headers=headers,
        json={"full_name": "Named Heir", "email": "heir@example.com", "relationship": "child"},
    ).json()["data"]


def test_create_inheritance_rule_for_beneficiary(client: TestClient, auth_headers: dict[str, str]):
    beneficiary = _create_beneficiary(client, auth_headers)

    response = client.post(
        "/api/v1/inheritance/rules",
        headers=auth_headers,
        json={
            "beneficiary_id": beneficiary["id"],
            "trigger": "death_verification",
            "conditions": {"min_trusted_contacts": 2},
            "instructions": "Release the estate documents to this heir.",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["beneficiary_id"] == beneficiary["id"]
    assert data["trigger"] == "death_verification"
    assert data["active"] is True
    # Encrypted instructions must never leak back through the API.
    assert "Release the estate documents" not in response.text


def test_create_rule_rejects_unknown_beneficiary(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/v1/inheritance/rules",
        headers=auth_headers,
        json={"beneficiary_id": "lv_does_not_exist", "trigger": "death_verification"},
    )

    assert response.status_code == 404
    assert response.json()["success"] is False

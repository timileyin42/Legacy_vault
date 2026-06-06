from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.domains.identity.models import User, UserRole


def _seed_estate(client: TestClient, headers: dict[str, str]):
    client.post(
        "/api/v1/vault/assets",
        headers=headers,
        json={"category": "investment", "name": "Equity Trust", "value_estimate": 12450000, "currency": "USD"},
    )
    client.post(
        "/api/v1/beneficiaries",
        headers=headers,
        json={"full_name": "Eleanor Thorne", "email": "eleanor@example.com", "relationship": "child", "allocation_percent": 100},
    )


def test_succession_report_generate_get_share(client: TestClient, auth_headers: dict[str, str]):
    _seed_estate(client, auth_headers)

    generate = client.post(
        "/api/v1/succession-reports",
        headers=auth_headers,
        json={"final_message": "Take care of each other."},
    )
    assert generate.status_code == 200
    report = generate.json()["data"]
    assert report["reference"].startswith("LV-")
    assert report["asset_transfer_summary"][0]["name"] == "Equity Trust"
    assert report["distribution"][0]["full_name"] == "Eleanor Thorne"
    assert report["status"] == "draft"

    listed = client.get("/api/v1/succession-reports", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1

    share = client.post(f"/api/v1/succession-reports/{report['id']}/share", headers=auth_headers)
    assert share.status_code == 200
    assert share.json()["data"]["share_token"]
    assert share.json()["data"]["status"] == "verified_released"


def test_admin_dashboard_users_and_actions(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
):
    # Non-admins are blocked from the admin surface.
    assert client.get("/api/v1/admin/dashboard", headers=auth_headers).status_code == 403

    user = db_session.query(User).filter(User.email == "owner@example.com").one()
    user.role = UserRole.admin
    db_session.commit()

    dashboard = client.get("/api/v1/admin/dashboard", headers=auth_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["data"]["total_users"] >= 1

    users = client.get("/api/v1/admin/users", headers=auth_headers)
    assert users.status_code == 200
    assert users.json()["data"]["total"] >= 1
    assert any(u["email"] == "owner@example.com" for u in users.json()["data"]["items"])

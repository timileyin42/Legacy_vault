from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.domains.identity.models import User, UserRole


def test_admin_verification_queue_requires_admin(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/admin/verification-queue", headers=auth_headers)

    assert response.status_code == 403
    assert response.json()["success"] is False


def test_admin_can_read_verification_queue(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
):
    user = db_session.query(User).filter(User.email == "owner@example.com").one()
    user.role = UserRole.admin
    db_session.commit()

    response = client.get("/api/v1/admin/verification-queue", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"] == []


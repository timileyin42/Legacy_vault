from fastapi.testclient import TestClient

from backend.app.core.security import generate_totp_code


def test_mfa_setup_encrypts_secret_and_verify_enables_mfa(
    client: TestClient,
    auth_headers: dict[str, str],
):
    setup_response = client.post("/api/v1/auth/mfa/setup", headers=auth_headers)

    assert setup_response.status_code == 200
    setup_data = setup_response.json()["data"]
    assert setup_data["provisioning_uri"].startswith("otpauth://totp/")

    code = generate_totp_code(setup_data["secret"])
    verify_response = client.post(
        "/api/v1/auth/mfa/verify",
        headers=auth_headers,
        json={"code": code},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["data"]["mfa_enabled"] is True


def test_mfa_rejects_invalid_code(client: TestClient, auth_headers: dict[str, str]):
    client.post("/api/v1/auth/mfa/setup", headers=auth_headers)

    response = client.post(
        "/api/v1/auth/mfa/verify",
        headers=auth_headers,
        json={"code": "000000"},
    )

    assert response.status_code == 400
    assert response.json()["success"] is False


from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.domains.vault.models import VaultItem


def test_vault_item_encrypts_sensitive_payload_and_hides_it_from_api(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
):
    response = client.post(
        "/api/v1/vault/items",
        headers=auth_headers,
        json={
            "category": "crypto_wallet",
            "title": "Cold wallet",
            "sensitive_payload": {
                "private_key": "never-return-this-secret",
                "seed_phrase": "alpha bravo charlie delta",
            },
            "masked_hint": "Ledger ending A7",
            "security_level": "critical",
            "release_policy": {"trigger": "death_verification"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Cold wallet"
    assert "sensitive_payload" not in body["data"]
    assert "never-return-this-secret" not in response.text

    stored = db_session.query(VaultItem).one()
    assert "never-return-this-secret" not in stored.payload_encrypted
    assert "Cold wallet" not in stored.title_encrypted


def test_document_does_not_return_storage_object(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/v1/vault/documents",
        headers=auth_headers,
        json={
            "title": "Last Will",
            "document_type": "will",
            "storage_object": "gs://private-bucket/estate/will.pdf",
            "checksum": "abc123456789def0",
            "classification": "legal",
        },
    )

    assert response.status_code == 200
    assert "storage_object" not in response.json()["data"]
    assert "private-bucket" not in response.text


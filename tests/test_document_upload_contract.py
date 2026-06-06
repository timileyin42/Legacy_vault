import hashlib
from dataclasses import dataclass

from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.domains.vault.models import Document
from backend.app.integrations.storage import StoredObject, get_storage_client


@dataclass
class FakeStorageClient:
    uploaded_key: str = "documents/lv_test/doc.pdf"

    def upload_document(self, *, owner_public_id: str, file: UploadFile) -> StoredObject:
        payload = file.file.read()
        return StoredObject(
            provider="cloudflare_r2",
            bucket="eterna-test",
            object_key=f"documents/{owner_public_id}/doc.pdf",
            checksum=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
            content_type=file.content_type or "application/octet-stream",
        )

    def create_presigned_read_url(self, *, object_key: str) -> str:
        return f"https://r2.example.test/{object_key}"


def test_document_upload_uses_storage_contract_and_encrypts_object_key(
    client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
):
    fake_storage = FakeStorageClient()
    client.app.dependency_overrides[get_storage_client] = lambda: fake_storage

    response = client.post(
        "/api/v1/vault/documents/upload",
        headers=auth_headers,
        data={"title": "Estate Deed", "document_type": "deed", "classification": "legal"},
        files={"file": ("deed.pdf", b"private document bytes", "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["upload_provider"] == "cloudflare_r2"
    assert data["file_name"] == "deed.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["byte_size"] == len(b"private document bytes")
    assert "documents/" not in response.text

    stored = db_session.query(Document).one()
    assert "documents/" not in stored.storage_object_encrypted

    url_response = client.post(
        f"/api/v1/vault/documents/{data['id']}/read-url",
        headers=auth_headers,
    )
    assert url_response.status_code == 200
    assert url_response.json()["data"]["read_url"].startswith("https://r2.example.test/documents/")


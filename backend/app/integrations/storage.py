import hashlib
import uuid
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, UploadFile, status

from backend.app.core.config import Settings, get_settings


@dataclass(frozen=True)
class StoredObject:
    provider: str
    bucket: str
    object_key: str
    checksum: str
    byte_size: int
    content_type: str


class StorageClient(Protocol):
    def upload_document(self, *, owner_public_id: str, file: UploadFile) -> StoredObject:
        ...

    def create_presigned_read_url(self, *, object_key: str) -> str:
        ...


class CloudflareR2StorageClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def upload_document(self, *, owner_public_id: str, file: UploadFile) -> StoredObject:
        self._require_configuration()
        payload = file.file.read()
        if not payload:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        checksum = hashlib.sha256(payload).hexdigest()
        object_key = f"documents/{owner_public_id}/{uuid.uuid4().hex}/{file.filename}"
        client = self._client()
        client.put_object(
            Bucket=self.settings.cloudflare_r2_bucket_name,
            Key=object_key,
            Body=payload,
            ContentType=file.content_type or "application/octet-stream",
            Metadata={"sha256": checksum, "owner": owner_public_id},
        )
        return StoredObject(
            provider="cloudflare_r2",
            bucket=self.settings.cloudflare_r2_bucket_name or "",
            object_key=object_key,
            checksum=checksum,
            byte_size=len(payload),
            content_type=file.content_type or "application/octet-stream",
        )

    def create_presigned_read_url(self, *, object_key: str) -> str:
        self._require_configuration()
        if self.settings.cloudflare_r2_public_base_url:
            return f"{self.settings.cloudflare_r2_public_base_url.rstrip('/')}/{object_key}"
        return self._client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.settings.cloudflare_r2_bucket_name, "Key": object_key},
            ExpiresIn=self.settings.cloudflare_r2_presigned_url_expire_seconds,
        )

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for Cloudflare R2 storage.") from exc
        endpoint_url = (
            f"https://{self.settings.cloudflare_r2_account_id}.r2.cloudflarestorage.com"
        )
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.settings.cloudflare_r2_access_key_id,
            aws_secret_access_key=self.settings.cloudflare_r2_secret_access_key,
            region_name="auto",
        )

    def _require_configuration(self) -> None:
        missing = [
            name
            for name in (
                "cloudflare_r2_account_id",
                "cloudflare_r2_access_key_id",
                "cloudflare_r2_secret_access_key",
                "cloudflare_r2_bucket_name",
            )
            if not getattr(self.settings, name)
        ]
        if missing:
            raise RuntimeError(f"Cloudflare R2 is not configured: {', '.join(missing)}")


def get_storage_client() -> StorageClient:
    return CloudflareR2StorageClient()


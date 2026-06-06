import json
from datetime import UTC, datetime

from fastapi import HTTPException, status
from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService
from backend.app.domains.identity.models import User
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.domains.vault.models import Asset, Document, VaultItem
from backend.app.domains.vault.repository import VaultRepository
from backend.app.domains.vault.schemas import (
    AssetCreateRequest,
    AssetResponse,
    AssetUpdateRequest,
    DocumentCategorySummary,
    DocumentCreateRequest,
    DocumentDetailResponse,
    DocumentExpiryAlert,
    DocumentReadUrlResponse,
    DocumentResponse,
    DocumentUploadResponse,
    VaultItemCreateRequest,
    VaultItemResponse,
    VaultItemUpdateRequest,
)
from backend.app.integrations.storage import StorageClient


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class VaultService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = VaultRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)

    def create_item(self, owner: User, request: VaultItemCreateRequest) -> VaultItemResponse:
        item = VaultItem(
            owner_id=owner.id,
            category=request.category,
            title_encrypted=self.encryption.encrypt(request.title),
            payload_encrypted=self.encryption.encrypt(json.dumps(request.sensitive_payload)),
            masked_hint=request.masked_hint,
            security_level=request.security_level,
            release_policy=request.release_policy,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_item(item)
        self.db.flush()
        self.audit.record(
            action=AuditAction.vault_item_created,
            actor_id=owner.id,
            resource_type="vault_item",
            resource_public_id=item.public_id,
        )
        return self._to_item_response(item)

    def list_items(self, owner: User) -> list[VaultItemResponse]:
        return [self._to_item_response(item) for item in self.repository.list_items(owner.id)]

    def get_item(self, owner: User, public_id: str) -> VaultItemResponse:
        item = self.repository.get_item(owner.id, public_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault item not found.")
        self.audit.record(
            action=AuditAction.vault_item_viewed,
            actor_id=owner.id,
            resource_type="vault_item",
            resource_public_id=item.public_id,
        )
        return self._to_item_response(item)

    def update_item(self, owner: User, public_id: str, request: VaultItemUpdateRequest) -> VaultItemResponse:
        item = self.repository.get_item(owner.id, public_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault item not found.")
        if request.title is not None:
            item.title_encrypted = self.encryption.encrypt(request.title)
        if request.sensitive_payload is not None:
            item.payload_encrypted = self.encryption.encrypt(json.dumps(request.sensitive_payload))
        if request.masked_hint is not None:
            item.masked_hint = request.masked_hint
        if request.security_level is not None:
            item.security_level = request.security_level
        if request.release_policy is not None:
            item.release_policy = request.release_policy
        item.updated_by = owner.id
        self.audit.record(
            action=AuditAction.vault_item_updated,
            actor_id=owner.id,
            resource_type="vault_item",
            resource_public_id=item.public_id,
        )
        return self._to_item_response(item)

    def delete_item(self, owner: User, public_id: str) -> dict:
        item = self.repository.get_item(owner.id, public_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault item not found.")
        item.is_deleted = True
        item.updated_by = owner.id
        self.audit.record(
            action=AuditAction.vault_item_deleted,
            actor_id=owner.id,
            resource_type="vault_item",
            resource_public_id=item.public_id,
        )
        return {"id": public_id, "deleted": True}

    def create_asset(self, owner: User, request: AssetCreateRequest) -> AssetResponse:
        asset = Asset(
            owner_id=owner.id,
            category=request.category,
            name_encrypted=self.encryption.encrypt(request.name),
            value_estimate=request.value_estimate,
            currency=request.currency.upper(),
            metadata_encrypted=self.encryption.encrypt(json.dumps(request.metadata)),
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_asset(asset)
        self.db.flush()
        return self._to_asset_response(asset)

    def list_assets(self, owner: User) -> list[AssetResponse]:
        return [self._to_asset_response(asset) for asset in self.repository.list_assets(owner.id)]

    def get_asset(self, owner: User, public_id: str) -> AssetResponse:
        asset = self.repository.get_asset(owner.id, public_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return self._to_asset_response(asset)

    def update_asset(self, owner: User, public_id: str, request: AssetUpdateRequest) -> AssetResponse:
        asset = self.repository.get_asset(owner.id, public_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        if request.category is not None:
            asset.category = request.category
        if request.name is not None:
            asset.name_encrypted = self.encryption.encrypt(request.name)
        if request.value_estimate is not None:
            asset.value_estimate = request.value_estimate
        if request.currency is not None:
            asset.currency = request.currency.upper()
        if request.metadata is not None:
            asset.metadata_encrypted = self.encryption.encrypt(json.dumps(request.metadata))
        asset.updated_by = owner.id
        self.audit.record(
            action=AuditAction.asset_updated,
            actor_id=owner.id,
            resource_type="asset",
            resource_public_id=asset.public_id,
        )
        return self._to_asset_response(asset)

    def delete_asset(self, owner: User, public_id: str) -> dict:
        asset = self.repository.get_asset(owner.id, public_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        asset.is_deleted = True
        asset.updated_by = owner.id
        self.audit.record(
            action=AuditAction.asset_deleted,
            actor_id=owner.id,
            resource_type="asset",
            resource_public_id=asset.public_id,
        )
        return {"id": public_id, "deleted": True}

    def create_document(self, owner: User, request: DocumentCreateRequest) -> DocumentResponse:
        document = Document(
            owner_id=owner.id,
            title_encrypted=self.encryption.encrypt(request.title),
            document_type=request.document_type,
            file_name=request.file_name,
            content_type=request.content_type,
            byte_size=request.byte_size,
            storage_object_encrypted=self.encryption.encrypt(request.storage_object),
            checksum=request.checksum,
            classification=request.classification,
            notarization_status=request.notarization_status,
            ocr_text_encrypted=self.encryption.encrypt(request.ocr_text) if request.ocr_text else None,
            expires_at=_parse_iso(request.expires_at),
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_document(document)
        self.db.flush()
        return self._to_document_response(document)

    def upload_document(
        self,
        owner: User,
        *,
        title: str,
        document_type: str,
        classification: str | None,
        file: UploadFile,
        storage_client: StorageClient,
    ) -> DocumentUploadResponse:
        stored = storage_client.upload_document(owner_public_id=owner.public_id, file=file)
        document = Document(
            owner_id=owner.id,
            title_encrypted=self.encryption.encrypt(title),
            document_type=document_type,
            file_name=file.filename,
            content_type=stored.content_type,
            byte_size=stored.byte_size,
            storage_provider=stored.provider,
            storage_object_encrypted=self.encryption.encrypt(stored.object_key),
            checksum=stored.checksum,
            classification=classification,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_document(document)
        self.db.flush()
        response = self._to_document_response(document)
        return DocumentUploadResponse(**response.model_dump(), upload_provider=stored.provider)

    def list_documents(self, owner: User) -> list[DocumentResponse]:
        return [self._to_document_response(document) for document in self.repository.list_documents(owner.id)]

    def get_document(self, owner: User, public_id: str) -> DocumentDetailResponse:
        document = self.repository.get_document(owner.id, public_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        base = self._to_document_response(document)
        ocr = self.encryption.decrypt(document.ocr_text_encrypted) if document.ocr_text_encrypted else None
        return DocumentDetailResponse(**base.model_dump(), ocr_text=ocr)

    def delete_document(self, owner: User, public_id: str) -> dict:
        document = self.repository.get_document(owner.id, public_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        document.is_deleted = True
        document.updated_by = owner.id
        self.audit.record(
            action=AuditAction.document_deleted,
            actor_id=owner.id,
            resource_type="document",
            resource_public_id=document.public_id,
        )
        return {"id": public_id, "deleted": True}

    def document_categories(self, owner: User) -> list[DocumentCategorySummary]:
        counts: dict[str, int] = {}
        for document in self.repository.list_documents(owner.id):
            key = document.document_type
            counts[key] = counts.get(key, 0) + 1
        return [DocumentCategorySummary(category=key, count=value) for key, value in sorted(counts.items())]

    def expiring_documents(self, owner: User, within_days: int = 60) -> list[DocumentExpiryAlert]:
        now = datetime.now(UTC)
        alerts: list[DocumentExpiryAlert] = []
        for document in self.repository.list_documents(owner.id):
            if not document.expires_at:
                continue
            expires_at = document.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            days_remaining = (expires_at - now).days
            if days_remaining <= within_days:
                alerts.append(
                    DocumentExpiryAlert(
                        id=document.public_id,
                        title=self.encryption.decrypt(document.title_encrypted),
                        document_type=document.document_type,
                        expires_at=expires_at.isoformat(),
                        days_remaining=days_remaining,
                    )
                )
        return sorted(alerts, key=lambda alert: alert.days_remaining)

    def create_document_read_url(
        self, owner: User, public_id: str, storage_client: StorageClient
    ) -> DocumentReadUrlResponse:
        document = self.repository.get_document(owner.id, public_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        object_key = self.encryption.decrypt(document.storage_object_encrypted)
        return DocumentReadUrlResponse(
            id=document.public_id,
            read_url=storage_client.create_presigned_read_url(object_key=object_key),
        )

    def _to_item_response(self, item: VaultItem) -> VaultItemResponse:
        return VaultItemResponse(
            id=item.public_id,
            category=item.category,
            title=self.encryption.decrypt(item.title_encrypted),
            masked_hint=item.masked_hint,
            security_level=item.security_level,
            release_policy=item.release_policy,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )

    def _to_asset_response(self, asset: Asset) -> AssetResponse:
        return AssetResponse(
            id=asset.public_id,
            category=asset.category,
            name=self.encryption.decrypt(asset.name_encrypted),
            value_estimate=float(asset.value_estimate) if asset.value_estimate is not None else None,
            currency=asset.currency,
        )

    def _to_document_response(self, document: Document) -> DocumentResponse:
        return DocumentResponse(
            id=document.public_id,
            title=self.encryption.decrypt(document.title_encrypted),
            document_type=document.document_type,
            file_name=document.file_name,
            content_type=document.content_type,
            byte_size=document.byte_size,
            storage_provider=document.storage_provider,
            checksum=document.checksum,
            classification=document.classification,
            integrity_status=document.integrity_status,
            notarization_status=document.notarization_status,
            version_count=document.version_count,
            expires_at=document.expires_at.isoformat() if document.expires_at else None,
        )

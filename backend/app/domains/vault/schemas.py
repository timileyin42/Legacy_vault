from pydantic import BaseModel, Field

from backend.app.domains.vault.models import SecurityLevel, VaultCategory


class VaultItemCreateRequest(BaseModel):
    category: VaultCategory
    title: str = Field(min_length=1, max_length=255)
    sensitive_payload: dict = Field(default_factory=dict)
    masked_hint: str | None = Field(default=None, max_length=128)
    security_level: SecurityLevel = SecurityLevel.high
    release_policy: dict = Field(default_factory=dict)


class VaultItemUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    sensitive_payload: dict | None = None
    masked_hint: str | None = Field(default=None, max_length=128)
    security_level: SecurityLevel | None = None
    release_policy: dict | None = None


class VaultItemResponse(BaseModel):
    id: str
    category: VaultCategory
    title: str
    masked_hint: str | None
    security_level: SecurityLevel
    release_policy: dict
    created_at: str
    updated_at: str


class AssetCreateRequest(BaseModel):
    category: VaultCategory
    name: str = Field(min_length=1, max_length=255)
    value_estimate: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    metadata: dict = Field(default_factory=dict)


class AssetUpdateRequest(BaseModel):
    category: VaultCategory | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    value_estimate: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    metadata: dict | None = None


class AssetResponse(BaseModel):
    id: str
    category: VaultCategory
    name: str
    value_estimate: float | None
    currency: str


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    document_type: str = Field(min_length=1, max_length=80)
    storage_object: str = Field(min_length=1, max_length=512)
    checksum: str = Field(min_length=16, max_length=128)
    classification: str | None = Field(default=None, max_length=80)
    file_name: str | None = Field(default=None, max_length=255)
    content_type: str | None = Field(default=None, max_length=120)
    byte_size: int | None = Field(default=None, ge=0)
    notarization_status: str | None = Field(default=None, max_length=80)
    ocr_text: str | None = Field(default=None, max_length=20000)
    expires_at: str | None = Field(default=None, description="ISO-8601 expiry timestamp.")

class DocumentResponse(BaseModel):
    id: str
    title: str
    document_type: str
    file_name: str | None
    content_type: str | None
    byte_size: int | None
    storage_provider: str
    checksum: str
    classification: str | None
    integrity_status: str
    notarization_status: str | None
    version_count: int
    expires_at: str | None = None


class DocumentUploadResponse(DocumentResponse):
    upload_provider: str


class DocumentReadUrlResponse(BaseModel):
    id: str
    read_url: str


class DocumentDetailResponse(DocumentResponse):
    ocr_text: str | None = None


class DocumentCategorySummary(BaseModel):
    category: str
    count: int


class DocumentExpiryAlert(BaseModel):
    id: str
    title: str
    document_type: str
    expires_at: str
    days_remaining: int

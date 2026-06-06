from pydantic import BaseModel, Field

from backend.app.domains.legacy.models import LegacyNoteStatus, LegacyReleaseTrigger, MediaType


class LegacyNoteCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(default="", max_length=20000)
    media_type: MediaType = MediaType.written
    media_object: str | None = Field(default=None, max_length=512)
    release_trigger: LegacyReleaseTrigger | None = None
    release_at: str | None = Field(default=None, description="ISO-8601 release timestamp.")
    beneficiary_id: str | None = None


class LegacyNoteUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, max_length=20000)
    media_type: MediaType | None = None
    media_object: str | None = Field(default=None, max_length=512)
    release_trigger: LegacyReleaseTrigger | None = None
    release_at: str | None = None


class LegacyNoteResponse(BaseModel):
    id: str
    title: str
    body: str
    media_type: MediaType
    has_media: bool
    status: LegacyNoteStatus
    release_trigger: LegacyReleaseTrigger | None
    release_at: str | None
    beneficiary_id: str | None
    created_at: str


class LegacyMemoryCreateRequest(BaseModel):
    caption: str | None = Field(default=None, max_length=255)
    storage_object: str = Field(min_length=1, max_length=512)
    content_type: str | None = Field(default=None, max_length=120)


class LegacyMemoryResponse(BaseModel):
    id: str
    caption: str | None
    content_type: str | None
    created_at: str

from pydantic import BaseModel, EmailStr, Field

from backend.app.domains.verification.models import StageStatus, VerificationStatus, WitnessStatus


class WitnessCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr


class DeathVerificationCreateRequest(BaseModel):
    certificate_file_name: str | None = Field(default=None, max_length=255)
    certificate_object: str | None = Field(default=None, max_length=512)
    certificate_checksum: str | None = Field(default=None, max_length=128)
    witnesses: list[WitnessCreateRequest] = Field(default_factory=list)


class WitnessRespondRequest(BaseModel):
    status: WitnessStatus


class StageUpdateRequest(BaseModel):
    document_integrity_status: StageStatus | None = None
    court_crosscheck_status: StageStatus | None = None
    vault_unlock_status: StageStatus | None = None


class WitnessResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    status: WitnessStatus
    responded_at: str | None


class DeathVerificationResponse(BaseModel):
    id: str
    status: VerificationStatus
    certificate_file_name: str | None
    certificate_uploaded: bool
    document_integrity_status: StageStatus
    court_crosscheck_status: StageStatus
    vault_unlock_status: StageStatus
    progress_percent: int
    witnesses: list[WitnessResponse]
    witness_consensus: str


class EmergencyAccessStatusResponse(BaseModel):
    has_active_verification: bool
    verification: DeathVerificationResponse | None
    waiting_period_days: int
    security_level: str

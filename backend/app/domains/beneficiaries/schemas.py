from pydantic import BaseModel, EmailStr, Field

from backend.app.domains.beneficiaries.models import BeneficiaryStatus


class BeneficiaryCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    relationship: str = Field(min_length=2, max_length=80)
    allocation_percent: int = Field(default=0, ge=0, le=100)
    instructions: str | None = Field(default=None, max_length=4000)


class BeneficiaryUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    relationship: str | None = Field(default=None, min_length=2, max_length=80)
    allocation_percent: int | None = Field(default=None, ge=0, le=100)
    instructions: str | None = Field(default=None, max_length=4000)


class BeneficiaryVerifyRequest(BaseModel):
    status: BeneficiaryStatus = BeneficiaryStatus.verified


class BeneficiaryResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    relationship: str
    status: BeneficiaryStatus
    allocation_percent: int


class BeneficiaryAllocationSummary(BaseModel):
    beneficiary_count: int
    total_allocated_percent: int
    unallocated_percent: int
    fully_allocated: bool


class TrustedContactCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    verification_weight: int = Field(default=1, ge=1, le=10)


class TrustedContactResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    verification_weight: int


from pydantic import BaseModel, Field

from backend.app.domains.inheritance.models import AccessRequestStatus, ReleaseTrigger


class InheritanceRuleCreateRequest(BaseModel):
    beneficiary_id: str
    vault_item_id: str | None = None
    trigger: ReleaseTrigger
    conditions: dict = Field(default_factory=dict)
    instructions: str | None = Field(default=None, max_length=4000)


class InheritanceRuleUpdateRequest(BaseModel):
    trigger: ReleaseTrigger | None = None
    conditions: dict | None = None
    instructions: str | None = Field(default=None, max_length=4000)
    active: bool | None = None


class RuleToggleRequest(BaseModel):
    active: bool


class InheritanceRuleResponse(BaseModel):
    id: str
    beneficiary_id: str
    vault_item_id: str | None
    trigger: ReleaseTrigger
    conditions: dict
    active: bool


class DistributionEntry(BaseModel):
    beneficiary_id: str
    full_name: str
    relationship: str
    allocation_percent: int


class DistributionSummaryResponse(BaseModel):
    entries: list[DistributionEntry]
    total_allocated_percent: int
    unallocated_percent: int
    active_rule_count: int
    engine_status: str


class AccessRequestCreateRequest(BaseModel):
    beneficiary_id: str
    request_type: ReleaseTrigger = ReleaseTrigger.death_verification
    evidence_summary: str = Field(min_length=8, max_length=4000)


class AccessRequestStatusRequest(BaseModel):
    status: AccessRequestStatus
    reviewer_notes: str | None = Field(default=None, max_length=4000)


class AccessRequestResponse(BaseModel):
    id: str
    beneficiary_id: str
    request_type: ReleaseTrigger
    status: AccessRequestStatus
    waiting_period_days: int
    release_at: str | None
    risk_score: int


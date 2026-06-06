from pydantic import BaseModel


class ReadinessBreakdownItem(BaseModel):
    label: str
    score: int


class ReadinessResponse(BaseModel):
    overall_score: int
    legal_documentation: int
    beneficiary_mapping: int
    security: int
    breakdown: list[ReadinessBreakdownItem]


class AssetDistributionEntry(BaseModel):
    category: str
    total_value: float
    percent: int


class AssetDistributionResponse(BaseModel):
    total_value: float
    currency: str
    entries: list[AssetDistributionEntry]


class BeneficiaryCoverageEntry(BaseModel):
    beneficiary_id: str
    full_name: str
    allocation_percent: int
    status: str


class BeneficiaryCoverageResponse(BaseModel):
    coverage_percent: int
    fully_allocated: bool
    entries: list[BeneficiaryCoverageEntry]


class SecurityMetricsResponse(BaseModel):
    encryption_standard: str
    mfa_enabled: bool
    biometric_enabled: bool
    active_sessions: int
    audit_log_health: str


class TrendPoint(BaseModel):
    period: str
    total_value: float


class TrendsResponse(BaseModel):
    points: list[TrendPoint]

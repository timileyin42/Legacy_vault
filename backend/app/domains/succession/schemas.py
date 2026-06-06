from pydantic import BaseModel, Field

from backend.app.domains.succession.models import SuccessionReportStatus


class SuccessionReportCreateRequest(BaseModel):
    final_message: str | None = Field(default=None, max_length=8000)


class AssetTransferEntry(BaseModel):
    name: str
    category: str
    value_estimate: float | None
    currency: str


class DistributionEntry(BaseModel):
    full_name: str
    relationship: str
    allocation_percent: int


class SuccessionReportResponse(BaseModel):
    id: str
    reference: str
    status: SuccessionReportStatus
    decedent_name: str
    content_hash: str
    final_message: str | None
    asset_transfer_summary: list[AssetTransferEntry]
    distribution: list[DistributionEntry]
    share_token: str | None
    released_at: str | None
    generated_at: str


class SuccessionReportSummary(BaseModel):
    id: str
    reference: str
    status: SuccessionReportStatus
    generated_at: str


class ShareResponse(BaseModel):
    id: str
    share_token: str
    status: SuccessionReportStatus

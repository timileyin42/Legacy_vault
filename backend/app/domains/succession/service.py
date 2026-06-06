import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
from backend.app.domains.identity.models import User
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.domains.succession.models import SuccessionReport, SuccessionReportStatus
from backend.app.domains.succession.repository import SuccessionRepository
from backend.app.domains.succession.schemas import (
    AssetTransferEntry,
    DistributionEntry,
    ShareResponse,
    SuccessionReportCreateRequest,
    SuccessionReportResponse,
    SuccessionReportSummary,
)
from backend.app.domains.vault.repository import VaultRepository


class SuccessionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = SuccessionRepository(db)
        self.vault = VaultRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)

    def generate(self, owner: User, request: SuccessionReportCreateRequest) -> SuccessionReportResponse:
        assets = self._asset_summary(owner)
        distribution = self._distribution(owner)
        digest_source = "|".join(
            [owner.public_id]
            + [f"{a.name}:{a.value_estimate}" for a in assets]
            + [f"{d.full_name}:{d.allocation_percent}" for d in distribution]
        )
        content_hash = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
        report = SuccessionReport(
            owner_id=owner.id,
            reference=f"LV-{owner.public_id[-8:].upper()}",
            status=SuccessionReportStatus.draft,
            content_hash=content_hash,
            final_message_encrypted=(
                self.encryption.encrypt(request.final_message) if request.final_message else None
            ),
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create(report)
        self.db.flush()
        self.audit.record(
            action=AuditAction.succession_report_generated,
            actor_id=owner.id,
            resource_type="succession_report",
            resource_public_id=report.public_id,
        )
        return self._to_response(owner, report, assets, distribution)

    def list_reports(self, owner: User) -> list[SuccessionReportSummary]:
        return [
            SuccessionReportSummary(
                id=report.public_id,
                reference=report.reference,
                status=report.status,
                generated_at=report.created_at.isoformat(),
            )
            for report in self.repository.list_for_owner(owner.id)
        ]

    def get_report(self, owner: User, public_id: str) -> SuccessionReportResponse:
        report = self._require(owner, public_id)
        return self._to_response(owner, report, self._asset_summary(owner), self._distribution(owner))

    def render_pdf(self, owner: User, public_id: str) -> tuple[str, bytes]:
        from backend.app.integrations.pdf import render_succession_report_pdf

        response = self.get_report(owner, public_id)
        return response.reference, render_succession_report_pdf(response.model_dump())

    def share(self, owner: User, public_id: str) -> ShareResponse:
        report = self._require(owner, public_id)
        report.share_token = secrets.token_urlsafe(24)
        report.status = SuccessionReportStatus.verified_released
        report.released_at = datetime.now(UTC)
        report.updated_by = owner.id
        return ShareResponse(id=report.public_id, share_token=report.share_token, status=report.status)

    def _asset_summary(self, owner: User) -> list[AssetTransferEntry]:
        return [
            AssetTransferEntry(
                name=self.encryption.decrypt(asset.name_encrypted),
                category=asset.category.value,
                value_estimate=float(asset.value_estimate) if asset.value_estimate is not None else None,
                currency=asset.currency,
            )
            for asset in self.vault.list_assets(owner.id)
        ]

    def _distribution(self, owner: User) -> list[DistributionEntry]:
        return [
            DistributionEntry(
                full_name=self.encryption.decrypt(b.full_name_encrypted),
                relationship=b.relationship,
                allocation_percent=b.allocation_percent,
            )
            for b in self.beneficiaries.list_for_owner(owner.id)
        ]

    def _require(self, owner: User, public_id: str) -> SuccessionReport:
        report = self.repository.get_for_owner(owner.id, public_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Succession report not found.")
        return report

    def _to_response(
        self,
        owner: User,
        report: SuccessionReport,
        assets: list[AssetTransferEntry],
        distribution: list[DistributionEntry],
    ) -> SuccessionReportResponse:
        return SuccessionReportResponse(
            id=report.public_id,
            reference=report.reference,
            status=report.status,
            decedent_name=owner.full_name,
            content_hash=report.content_hash,
            final_message=(
                self.encryption.decrypt(report.final_message_encrypted)
                if report.final_message_encrypted
                else None
            ),
            asset_transfer_summary=assets,
            distribution=distribution,
            share_token=report.share_token,
            released_at=report.released_at.isoformat() if report.released_at else None,
            generated_at=report.created_at.isoformat(),
        )

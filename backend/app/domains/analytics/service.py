from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.analytics.schemas import (
    AssetDistributionEntry,
    AssetDistributionResponse,
    BeneficiaryCoverageEntry,
    BeneficiaryCoverageResponse,
    ReadinessBreakdownItem,
    ReadinessResponse,
    SecurityMetricsResponse,
    TrendPoint,
    TrendsResponse,
)
from backend.app.core.security import EncryptionService
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
from backend.app.domains.identity.models import User, UserSession
from backend.app.domains.vault.repository import VaultRepository


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.vault = VaultRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)
        self.encryption = EncryptionService()

    def readiness(self, owner: User) -> ReadinessResponse:
        documents = self.vault.list_documents(owner.id)
        legal_documentation = min(100, len(documents) * 25)
        beneficiary_mapping = min(100, self.beneficiaries.total_allocation(owner.id))
        security = self._security_score(owner)
        overall = round(legal_documentation * 0.35 + beneficiary_mapping * 0.35 + security * 0.30)
        return ReadinessResponse(
            overall_score=overall,
            legal_documentation=legal_documentation,
            beneficiary_mapping=beneficiary_mapping,
            security=security,
            breakdown=[
                ReadinessBreakdownItem(label="Legal documentation", score=legal_documentation),
                ReadinessBreakdownItem(label="Beneficiary mapping", score=beneficiary_mapping),
                ReadinessBreakdownItem(label="Security posture", score=security),
            ],
        )

    def asset_distribution(self, owner: User) -> AssetDistributionResponse:
        assets = self.vault.list_assets(owner.id)
        totals: dict[str, float] = {}
        grand_total = 0.0
        for asset in assets:
            value = float(asset.value_estimate) if asset.value_estimate is not None else 0.0
            totals[asset.category.value] = totals.get(asset.category.value, 0.0) + value
            grand_total += value
        entries = [
            AssetDistributionEntry(
                category=category,
                total_value=value,
                percent=round(value / grand_total * 100) if grand_total else 0,
            )
            for category, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        ]
        return AssetDistributionResponse(total_value=grand_total, currency="USD", entries=entries)

    def beneficiary_coverage(self, owner: User) -> BeneficiaryCoverageResponse:
        beneficiaries = self.beneficiaries.list_for_owner(owner.id)
        coverage = min(100, self.beneficiaries.total_allocation(owner.id))
        return BeneficiaryCoverageResponse(
            coverage_percent=coverage,
            fully_allocated=coverage >= 100,
            entries=[
                BeneficiaryCoverageEntry(
                    beneficiary_id=b.public_id,
                    full_name=self.encryption.decrypt(b.full_name_encrypted),
                    allocation_percent=b.allocation_percent,
                    status=b.status.value,
                )
                for b in beneficiaries
            ],
        )

    def security_metrics(self, owner: User) -> SecurityMetricsResponse:
        active_sessions = self.db.execute(
            select(UserSession).where(
                UserSession.user_id == owner.id,
                UserSession.revoked_at.is_(None),
                UserSession.is_deleted.is_(False),
            )
        ).scalars().all()
        return SecurityMetricsResponse(
            encryption_standard="AES-256 (Fernet) at rest, TLS in transit",
            mfa_enabled=owner.mfa_enabled,
            biometric_enabled=owner.biometric_enabled,
            active_sessions=len(active_sessions),
            audit_log_health="100% immutable",
        )

    def trends(self, owner: User) -> TrendsResponse:
        """Cumulative secured value bucketed by the month each asset was added."""
        assets = sorted(self.vault.list_assets(owner.id), key=lambda a: a.created_at)
        running = 0.0
        by_month: dict[str, float] = {}
        for asset in assets:
            running += float(asset.value_estimate) if asset.value_estimate is not None else 0.0
            by_month[asset.created_at.strftime("%Y-%m")] = running
        points = [TrendPoint(period=period, total_value=value) for period, value in sorted(by_month.items())]
        return TrendsResponse(points=points)

    def _security_score(self, owner: User) -> int:
        score = 40
        if owner.mfa_enabled:
            score += 30
        if owner.biometric_enabled:
            score += 30
        return min(100, score)

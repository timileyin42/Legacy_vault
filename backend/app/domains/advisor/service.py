from sqlalchemy.orm import Session

from backend.app.domains.advisor.schemas import (
    ChatResponse,
    RecommendationItem,
    RecommendationsResponse,
    RiskAnalysisResponse,
    RiskInsight,
)
from backend.app.domains.analytics.service import AnalyticsService
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
from backend.app.domains.identity.models import User
from backend.app.domains.vault.models import VaultCategory
from backend.app.domains.vault.repository import VaultRepository


class AdvisorService:
    """Deterministic, data-driven legacy advisor (no external LLM).

    Recommendations, risk insights, and chat replies are derived from the user's
    actual estate data so the screen is functional and private by default.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.analytics = AnalyticsService(db)
        self.vault = VaultRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)

    def recommendations(self, owner: User) -> RecommendationsResponse:
        readiness = self.analytics.readiness(owner)
        items: list[RecommendationItem] = []
        beneficiary_count = self.beneficiaries.count_for_owner(owner.id)
        total_allocation = self.beneficiaries.total_allocation(owner.id)
        documents = self.vault.list_documents(owner.id)
        assets = self.vault.list_assets(owner.id)

        if beneficiary_count == 0:
            items.append(
                RecommendationItem(
                    title="Add your first beneficiary",
                    detail="No beneficiaries are designated. Your estate cannot be transferred without them.",
                    priority="high",
                    action="add_beneficiary",
                )
            )
        if beneficiary_count and total_allocation < 100:
            items.append(
                RecommendationItem(
                    title="Complete your allocation",
                    detail=f"Only {min(total_allocation, 100)}% of your estate is allocated. Assign the remainder.",
                    priority="high",
                    action="edit_allocation",
                )
            )
        if not documents:
            items.append(
                RecommendationItem(
                    title="Upload your legal documents",
                    detail="Add your will, trust, and insurance documents to strengthen your estate.",
                    priority="medium",
                    action="upload_document",
                )
            )
        if not owner.mfa_enabled:
            items.append(
                RecommendationItem(
                    title="Enable multi-factor authentication",
                    detail="MFA protects access to your vault and improves your security score.",
                    priority="medium",
                    action="enable_mfa",
                )
            )
        if not assets:
            items.append(
                RecommendationItem(
                    title="Catalog your assets",
                    detail="Add financial, crypto, and property assets so they are never lost.",
                    priority="low",
                    action="add_asset",
                )
            )
        return RecommendationsResponse(completion_percent=readiness.overall_score, items=items)

    def risk_analysis(self, owner: User) -> RiskAnalysisResponse:
        assets = self.vault.list_assets(owner.id)
        total_value = sum(float(a.value_estimate or 0) for a in assets)
        crypto_value = sum(
            float(a.value_estimate or 0) for a in assets if a.category == VaultCategory.crypto_wallet
        )
        crypto_share = round(crypto_value / total_value * 100) if total_value else 0
        total_allocation = self.beneficiaries.total_allocation(owner.id)
        has_documents = bool(self.vault.list_documents(owner.id))

        volatility_level = "high" if crypto_share >= 50 else "medium" if crypto_share >= 20 else "low"
        contestation_score = max(0, 100 - min(total_allocation, 100)) + (0 if has_documents else 25)
        contestation_score = min(100, contestation_score)
        contestation_level = (
            "high" if contestation_score >= 60 else "medium" if contestation_score >= 30 else "low"
        )
        return RiskAnalysisResponse(
            insights=[
                RiskInsight(label="Asset volatility", level=volatility_level, score=crypto_share),
                RiskInsight(label="Legal contestation", level=contestation_level, score=contestation_score),
            ]
        )

    def chat(self, owner: User, message: str) -> ChatResponse:
        readiness = self.analytics.readiness(owner)
        recommendations = self.recommendations(owner)
        top = recommendations.items[0] if recommendations.items else None
        if top:
            reply = (
                f"Your estate is {readiness.overall_score}% ready. The most impactful next step is "
                f"\"{top.title}\": {top.detail}"
            )
        else:
            reply = (
                f"Your estate is {readiness.overall_score}% ready and well structured. "
                "Keep your documents and allocations up to date."
            )
        suggestions = [item.title for item in recommendations.items[:3]] or [
            "Review your beneficiaries",
            "Check document expiry dates",
        ]
        return ChatResponse(reply=reply, suggestions=suggestions)

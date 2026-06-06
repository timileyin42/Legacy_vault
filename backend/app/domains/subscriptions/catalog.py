"""Static plan catalogue for the pricing & subscriptions screen.

``beneficiary_limit`` of ``None`` means unlimited. Prices are in USD; the yearly
price reflects the discounted annual total shown on the pricing screen.
"""

from backend.app.domains.subscriptions.models import PlanTier

PLAN_CATALOG: dict[PlanTier, dict] = {
    PlanTier.free: {
        "name": "Free",
        "monthly_price": 0,
        "yearly_price": 0,
        "beneficiary_limit": 2,
        "storage_gb": 2,
        "features": [
            "Basic digital vault",
            "1 trusted contact",
            "2 beneficiaries",
            "2 GB encrypted storage",
        ],
    },
    PlanTier.premium: {
        "name": "Premium",
        "monthly_price": 49,
        "yearly_price": 468,
        "beneficiary_limit": 5,
        "storage_gb": 100,
        "features": [
            "Unlimited assets",
            "5 beneficiaries",
            "AI legacy advisor",
            "Quantum-grade encryption",
            "24/7 priority support",
        ],
        "recommended": True,
    },
    PlanTier.family: {
        "name": "Family",
        "monthly_price": 99,
        "yearly_price": 948,
        "beneficiary_limit": None,
        "storage_gb": None,
        "features": [
            "Multi-account family vault",
            "Unlimited beneficiaries",
            "Unlimited storage",
            "Concierge onboarding",
            "Physical vault backup",
        ],
    },
}

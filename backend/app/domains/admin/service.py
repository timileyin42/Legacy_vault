from fastapi import HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.app.domains.beneficiaries.models import Beneficiary
from backend.app.domains.identity.models import User
from backend.app.domains.inheritance.models import AccessRequest, AccessRequestStatus
from backend.app.domains.vault.models import Asset, VaultItem

_PENDING_STATUSES = (
    AccessRequestStatus.submitted,
    AccessRequestStatus.identity_verification,
    AccessRequestStatus.evidence_review,
    AccessRequestStatus.waiting_period,
)


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self) -> dict:
        total_users = self.db.execute(
            select(func.count()).select_from(User).where(User.is_deleted.is_(False))
        ).scalar_one()
        pending_verifications = self.db.execute(
            select(func.count())
            .select_from(AccessRequest)
            .where(AccessRequest.is_deleted.is_(False), AccessRequest.status.in_(_PENDING_STATUSES))
        ).scalar_one()
        active_vaults = self.db.execute(
            select(func.count(distinct(VaultItem.owner_id))).where(VaultItem.is_deleted.is_(False))
        ).scalar_one()
        total_aum = self.db.execute(
            select(func.coalesce(func.sum(Asset.value_estimate), 0)).where(Asset.is_deleted.is_(False))
        ).scalar_one()
        return {
            "total_users": int(total_users),
            "pending_verifications": int(pending_verifications),
            "active_vaults": int(active_vaults),
            "total_aum": float(total_aum),
            "currency": "USD",
        }

    def list_users(self, page: int = 1, page_size: int = 25) -> dict:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        total = self.db.execute(
            select(func.count()).select_from(User).where(User.is_deleted.is_(False))
        ).scalar_one()
        rows = list(
            self.db.execute(
                select(User)
                .where(User.is_deleted.is_(False))
                .order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars()
        )
        return {
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "items": [
                {
                    "id": user.public_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value,
                    "mfa_enabled": user.mfa_enabled,
                    "created_at": user.created_at.isoformat(),
                }
                for user in rows
            ],
        }

    def verification_queue(self) -> list[dict]:
        rows = list(
            self.db.execute(
                select(AccessRequest, Beneficiary)
                .join(Beneficiary, Beneficiary.id == AccessRequest.beneficiary_id)
                .where(AccessRequest.is_deleted.is_(False))
                .order_by(AccessRequest.created_at.asc())
                .limit(100)
            ).all()
        )
        return [
            {
                "id": access_request.public_id,
                "owner_id": str(access_request.owner_id),
                "beneficiary_id": beneficiary.public_id,
                "request_type": access_request.request_type.value,
                "status": access_request.status.value,
                "risk_score": access_request.risk_score,
                "created_at": access_request.created_at.isoformat(),
            }
            for access_request, beneficiary in rows
        ]

    def set_verification_status(self, public_id: str, new_status: AccessRequestStatus) -> dict:
        access_request = self.db.execute(
            select(AccessRequest).where(
                AccessRequest.public_id == public_id, AccessRequest.is_deleted.is_(False)
            )
        ).scalar_one_or_none()
        if not access_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found.")
        access_request.status = new_status
        return {"id": public_id, "status": new_status.value}

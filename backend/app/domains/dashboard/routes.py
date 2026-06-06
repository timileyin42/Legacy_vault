from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.beneficiaries.models import Beneficiary
from backend.app.domains.identity.models import User
from backend.app.domains.inheritance.models import AccessRequest
from backend.app.domains.vault.models import Asset, VaultItem

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vault_count = db.execute(
        select(func.count()).select_from(VaultItem).where(
            VaultItem.owner_id == current_user.id,
            VaultItem.is_deleted.is_(False),
        )
    ).scalar_one()
    asset_count = db.execute(
        select(func.count()).select_from(Asset).where(
            Asset.owner_id == current_user.id,
            Asset.is_deleted.is_(False),
        )
    ).scalar_one()
    beneficiary_count = db.execute(
        select(func.count()).select_from(Beneficiary).where(
            Beneficiary.owner_id == current_user.id,
            Beneficiary.is_deleted.is_(False),
        )
    ).scalar_one()
    access_request_count = db.execute(
        select(func.count()).select_from(AccessRequest).where(
            AccessRequest.owner_id == current_user.id,
            AccessRequest.is_deleted.is_(False),
        )
    ).scalar_one()
    readiness_score = min(100, 20 + vault_count * 10 + beneficiary_count * 20)
    return success_response(
        "Dashboard summary retrieved.",
        {
            "vault_items": vault_count,
            "assets": asset_count,
            "beneficiaries": beneficiary_count,
            "access_requests": access_request_count,
            "inheritance_readiness_score": readiness_score,
        },
    )


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import require_admin
from backend.app.core.responses import success_response
from backend.app.domains.admin.service import AdminService
from backend.app.domains.identity.models import User
from backend.app.domains.inheritance.models import AccessRequestStatus

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/dashboard")
def dashboard(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return success_response("Admin dashboard retrieved.", AdminService(db).dashboard())


@router.get("/users")
def list_users(
    page: int = 1,
    page_size: int = 25,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return success_response("Users retrieved.", AdminService(db).list_users(page=page, page_size=page_size))


@router.get("/verification-queue")
def verification_queue(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return success_response("Verification queue retrieved.", AdminService(db).verification_queue())


@router.post("/verifications/{public_id}/approve")
def approve_verification(
    public_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response = AdminService(db).set_verification_status(public_id, AccessRequestStatus.approved)
    db.commit()
    return success_response("Verification approved.", response)


@router.post("/verifications/{public_id}/reject")
def reject_verification(
    public_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    response = AdminService(db).set_verification_status(public_id, AccessRequestStatus.rejected)
    db.commit()
    return success_response("Verification rejected.", response)

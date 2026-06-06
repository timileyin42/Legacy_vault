from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.verification.schemas import (
    DeathVerificationCreateRequest,
    StageUpdateRequest,
    WitnessCreateRequest,
    WitnessRespondRequest,
)
from backend.app.domains.verification.service import VerificationService

router = APIRouter(prefix="/verification", tags=["Verification"])


@router.post("/death")
def create_death_verification(
    request: DeathVerificationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VerificationService(db).create_death_verification(current_user, request)
    db.commit()
    return success_response("Death verification submitted.", response.model_dump())


@router.get("/death")
def list_death_verifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VerificationService(db).list_death_verifications(current_user)
    return success_response("Death verifications retrieved.", [item.model_dump() for item in response])


@router.get("/emergency-access")
def emergency_access_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VerificationService(db).emergency_access_status(current_user)
    return success_response("Emergency access status retrieved.", response.model_dump())


@router.get("/death/{public_id}")
def get_death_verification(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VerificationService(db).get_death_verification(current_user, public_id)
    return success_response("Death verification retrieved.", response.model_dump())


@router.post("/death/{public_id}/witnesses")
def add_witness(
    public_id: str,
    request: WitnessCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VerificationService(db).add_witness(current_user, public_id, request)
    db.commit()
    return success_response("Witness added.", response.model_dump())


@router.post("/death/{public_id}/witnesses/{witness_public_id}/respond")
def respond_witness(
    public_id: str,
    witness_public_id: str,
    request: WitnessRespondRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VerificationService(db).respond_witness(current_user, public_id, witness_public_id, request)
    db.commit()
    return success_response("Witness response recorded.", response.model_dump())


@router.patch("/death/{public_id}/stages")
def update_stages(
    public_id: str,
    request: StageUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VerificationService(db).update_stages(current_user, public_id, request)
    db.commit()
    return success_response("Verification pipeline updated.", response.model_dump())

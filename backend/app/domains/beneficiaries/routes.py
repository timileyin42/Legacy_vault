from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.beneficiaries.schemas import (
    BeneficiaryCreateRequest,
    BeneficiaryUpdateRequest,
    BeneficiaryVerifyRequest,
    TrustedContactCreateRequest,
)
from backend.app.domains.beneficiaries.service import BeneficiaryService, TrustedContactService
from backend.app.domains.identity.models import User
from backend.app.integrations.email import (
    ResendEmailClient,
    build_heir_designation_email,
    get_email_client,
    safe_send,
)

router = APIRouter(prefix="/beneficiaries", tags=["Beneficiaries"])
trusted_contacts_router = APIRouter(prefix="/trusted-contacts", tags=["Trusted Contacts"])


@router.post("")
def create_beneficiary(
    request: BeneficiaryCreateRequest,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    email_client: ResendEmailClient = Depends(get_email_client),
    db: Session = Depends(get_db),
):
    response = BeneficiaryService(db).create(current_user, request)
    db.commit()
    # Notify the newly designated heir (stitch heir-designation template); best-effort delivery.
    background.add_task(
        safe_send,
        email_client,
        build_heir_designation_email(
            to=response.email, heir_name=response.full_name, owner_name=current_user.full_name
        ),
    )
    return success_response("Beneficiary created.", response.model_dump())


@router.get("")
def list_beneficiaries(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = BeneficiaryService(db).list_for_owner(current_user)
    return success_response("Beneficiaries retrieved.", [item.model_dump() for item in response])


@router.get("/summary")
def allocation_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = BeneficiaryService(db).allocation_summary(current_user)
    return success_response("Allocation summary retrieved.", response.model_dump())


@router.get("/{public_id}")
def get_beneficiary(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = BeneficiaryService(db).get(current_user, public_id)
    return success_response("Beneficiary retrieved.", response.model_dump())


@router.put("/{public_id}")
def update_beneficiary(
    public_id: str,
    request: BeneficiaryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = BeneficiaryService(db).update(current_user, public_id, request)
    db.commit()
    return success_response("Beneficiary updated.", response.model_dump())


@router.delete("/{public_id}")
def delete_beneficiary(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = BeneficiaryService(db).delete(current_user, public_id)
    db.commit()
    return success_response("Beneficiary removed.", response)


@router.post("/{public_id}/verify")
def verify_beneficiary(
    public_id: str,
    request: BeneficiaryVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = BeneficiaryService(db).verify(current_user, public_id, request)
    db.commit()
    return success_response("Beneficiary verification updated.", response.model_dump())


@trusted_contacts_router.post("")
def create_trusted_contact(
    request: TrustedContactCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = TrustedContactService(db).create(current_user, request)
    db.commit()
    return success_response("Trusted contact created.", response.model_dump())


@trusted_contacts_router.get("")
def list_trusted_contacts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = TrustedContactService(db).list_for_owner(current_user)
    return success_response("Trusted contacts retrieved.", [item.model_dump() for item in response])

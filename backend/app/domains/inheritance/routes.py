from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.inheritance.schemas import (
    AccessRequestCreateRequest,
    AccessRequestStatusRequest,
    InheritanceRuleCreateRequest,
    InheritanceRuleUpdateRequest,
    RuleToggleRequest,
)
from backend.app.domains.inheritance.service import InheritanceService

router = APIRouter(prefix="/inheritance", tags=["Inheritance"])


@router.post("/rules")
def create_rule(
    request: InheritanceRuleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = InheritanceService(db).create_rule(current_user, request)
    db.commit()
    return success_response("Inheritance rule created.", response.model_dump())


@router.get("/rules")
def list_rules(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = InheritanceService(db).list_rules(current_user)
    return success_response("Inheritance rules retrieved.", [item.model_dump() for item in response])


@router.get("/rules/distribution-summary")
def distribution_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = InheritanceService(db).distribution_summary(current_user)
    return success_response("Distribution summary retrieved.", response.model_dump())


@router.get("/rules/{public_id}")
def get_rule(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = InheritanceService(db).get_rule(current_user, public_id)
    return success_response("Inheritance rule retrieved.", response.model_dump())


@router.put("/rules/{public_id}")
def update_rule(
    public_id: str,
    request: InheritanceRuleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = InheritanceService(db).update_rule(current_user, public_id, request)
    db.commit()
    return success_response("Inheritance rule updated.", response.model_dump())


@router.post("/rules/{public_id}/toggle")
def toggle_rule(
    public_id: str,
    request: RuleToggleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = InheritanceService(db).toggle_rule(current_user, public_id, request)
    db.commit()
    return success_response("Inheritance rule toggled.", response.model_dump())


@router.post("/access-requests")
def create_access_request(
    request: AccessRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = InheritanceService(db).create_access_request(current_user, request)
    db.commit()
    return success_response("Access request submitted.", response.model_dump())


@router.get("/access-requests")
def list_access_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = InheritanceService(db).list_access_requests(current_user)
    return success_response("Access requests retrieved.", [item.model_dump() for item in response])


@router.patch("/access-requests/{public_id}/status")
def update_access_request_status(
    public_id: str,
    request: AccessRequestStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = InheritanceService(db).update_access_status(current_user, public_id, request)
    db.commit()
    return success_response("Access request status updated.", response.model_dump())


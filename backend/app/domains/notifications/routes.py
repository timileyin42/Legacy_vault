from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.notifications.schemas import DeviceTokenRegisterRequest
from backend.app.domains.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/devices")
def register_device(
    request: DeviceTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = NotificationService(db).register_device(current_user, request)
    db.commit()
    return success_response("Device registered for push notifications.", response.model_dump())


@router.get("/devices")
def list_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = NotificationService(db).list_devices(current_user)
    return success_response("Devices retrieved.", [item.model_dump() for item in response])


@router.get("")
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = NotificationService(db).list_notifications(current_user)
    return success_response("Notifications retrieved.", response.model_dump())


@router.post("/{public_id}/read")
def mark_read(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = NotificationService(db).mark_read(current_user, public_id)
    db.commit()
    return success_response("Notification marked read.", response.model_dump())


@router.post("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = NotificationService(db).mark_all_read(current_user)
    db.commit()
    return success_response("All notifications marked read.", response)

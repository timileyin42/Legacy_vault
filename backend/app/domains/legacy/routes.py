from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.legacy.schemas import (
    LegacyMemoryCreateRequest,
    LegacyNoteCreateRequest,
    LegacyNoteUpdateRequest,
)
from backend.app.domains.legacy.service import LegacyService

router = APIRouter(prefix="/legacy", tags=["Legacy Vault"])


@router.post("/notes")
def create_note(
    request: LegacyNoteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = LegacyService(db).create_note(current_user, request)
    db.commit()
    return success_response("Legacy note created.", response.model_dump())


@router.get("/notes")
def list_notes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = LegacyService(db).list_notes(current_user)
    return success_response("Legacy notes retrieved.", [item.model_dump() for item in response])


@router.get("/notes/scheduled")
def list_scheduled(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = LegacyService(db).list_scheduled(current_user)
    return success_response("Scheduled releases retrieved.", [item.model_dump() for item in response])


@router.get("/notes/{public_id}")
def get_note(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = LegacyService(db).get_note(current_user, public_id)
    return success_response("Legacy note retrieved.", response.model_dump())


@router.put("/notes/{public_id}")
def update_note(
    public_id: str,
    request: LegacyNoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = LegacyService(db).update_note(current_user, public_id, request)
    db.commit()
    return success_response("Legacy note updated.", response.model_dump())


@router.delete("/notes/{public_id}")
def delete_note(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = LegacyService(db).delete_note(current_user, public_id)
    db.commit()
    return success_response("Legacy note removed.", response)


@router.post("/memories")
def create_memory(
    request: LegacyMemoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = LegacyService(db).create_memory(current_user, request)
    db.commit()
    return success_response("Memory stored.", response.model_dump())


@router.get("/memories")
def list_memories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = LegacyService(db).list_memories(current_user)
    return success_response("Memories retrieved.", [item.model_dump() for item in response])

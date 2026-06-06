from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
from backend.app.domains.identity.models import User
from backend.app.domains.legacy.models import LegacyMemory, LegacyNote, LegacyNoteStatus
from backend.app.domains.legacy.repository import LegacyRepository
from backend.app.domains.legacy.schemas import (
    LegacyMemoryCreateRequest,
    LegacyMemoryResponse,
    LegacyNoteCreateRequest,
    LegacyNoteResponse,
    LegacyNoteUpdateRequest,
)
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LegacyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = LegacyRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)

    def create_note(self, owner: User, request: LegacyNoteCreateRequest) -> LegacyNoteResponse:
        beneficiary_id = None
        if request.beneficiary_id:
            beneficiary = self.beneficiaries.get_for_owner(owner.id, request.beneficiary_id)
            if not beneficiary:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found.")
            beneficiary_id = beneficiary.id
        note = LegacyNote(
            owner_id=owner.id,
            title_encrypted=self.encryption.encrypt(request.title),
            body_encrypted=self.encryption.encrypt(request.body or ""),
            media_type=request.media_type,
            media_object_encrypted=(
                self.encryption.encrypt(request.media_object) if request.media_object else None
            ),
            status=LegacyNoteStatus.scheduled if request.release_trigger else LegacyNoteStatus.draft,
            release_trigger=request.release_trigger,
            release_at=_parse_iso(request.release_at),
            beneficiary_id=beneficiary_id,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_note(note)
        self.db.flush()
        self.audit.record(
            action=AuditAction.legacy_note_created,
            actor_id=owner.id,
            resource_type="legacy_note",
            resource_public_id=note.public_id,
        )
        return self._to_note_response(owner, note)

    def list_notes(self, owner: User) -> list[LegacyNoteResponse]:
        return [self._to_note_response(owner, note) for note in self.repository.list_notes(owner.id)]

    def list_scheduled(self, owner: User) -> list[LegacyNoteResponse]:
        return [
            self._to_note_response(owner, note)
            for note in self.repository.list_notes(owner.id)
            if note.status == LegacyNoteStatus.scheduled
        ]

    def get_note(self, owner: User, public_id: str) -> LegacyNoteResponse:
        return self._to_note_response(owner, self._require(owner, public_id))

    def update_note(self, owner: User, public_id: str, request: LegacyNoteUpdateRequest) -> LegacyNoteResponse:
        note = self._require(owner, public_id)
        if request.title is not None:
            note.title_encrypted = self.encryption.encrypt(request.title)
        if request.body is not None:
            note.body_encrypted = self.encryption.encrypt(request.body)
        if request.media_type is not None:
            note.media_type = request.media_type
        if request.media_object is not None:
            note.media_object_encrypted = (
                self.encryption.encrypt(request.media_object) if request.media_object else None
            )
        if request.release_trigger is not None:
            note.release_trigger = request.release_trigger
            note.status = LegacyNoteStatus.scheduled
        if request.release_at is not None:
            note.release_at = _parse_iso(request.release_at)
        note.updated_by = owner.id
        return self._to_note_response(owner, note)

    def delete_note(self, owner: User, public_id: str) -> dict:
        note = self._require(owner, public_id)
        note.is_deleted = True
        note.updated_by = owner.id
        return {"id": public_id, "deleted": True}

    def create_memory(self, owner: User, request: LegacyMemoryCreateRequest) -> LegacyMemoryResponse:
        memory = LegacyMemory(
            owner_id=owner.id,
            caption=request.caption,
            storage_object_encrypted=self.encryption.encrypt(request.storage_object),
            content_type=request.content_type,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_memory(memory)
        self.db.flush()
        return self._to_memory_response(memory)

    def list_memories(self, owner: User) -> list[LegacyMemoryResponse]:
        return [self._to_memory_response(memory) for memory in self.repository.list_memories(owner.id)]

    def _require(self, owner: User, public_id: str) -> LegacyNote:
        note = self.repository.get_note(owner.id, public_id)
        if not note:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legacy note not found.")
        return note

    def _to_note_response(self, owner: User, note: LegacyNote) -> LegacyNoteResponse:
        beneficiary_public_id = None
        if note.beneficiary_id:
            for beneficiary in self.beneficiaries.list_for_owner(owner.id):
                if beneficiary.id == note.beneficiary_id:
                    beneficiary_public_id = beneficiary.public_id
                    break
        return LegacyNoteResponse(
            id=note.public_id,
            title=self.encryption.decrypt(note.title_encrypted),
            body=self.encryption.decrypt(note.body_encrypted),
            media_type=note.media_type,
            has_media=note.media_object_encrypted is not None,
            status=note.status,
            release_trigger=note.release_trigger,
            release_at=note.release_at.isoformat() if note.release_at else None,
            beneficiary_id=beneficiary_public_id,
            created_at=note.created_at.isoformat(),
        )

    def _to_memory_response(self, memory: LegacyMemory) -> LegacyMemoryResponse:
        return LegacyMemoryResponse(
            id=memory.public_id,
            caption=memory.caption,
            content_type=memory.content_type,
            created_at=memory.created_at.isoformat(),
        )

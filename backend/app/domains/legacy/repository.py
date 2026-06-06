import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.legacy.models import LegacyMemory, LegacyNote


class LegacyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_note(self, note: LegacyNote) -> LegacyNote:
        self.db.add(note)
        return note

    def list_notes(self, owner_id: uuid.UUID) -> list[LegacyNote]:
        return list(
            self.db.execute(
                select(LegacyNote)
                .where(LegacyNote.owner_id == owner_id, LegacyNote.is_deleted.is_(False))
                .order_by(LegacyNote.created_at.desc())
            ).scalars()
        )

    def get_note(self, owner_id: uuid.UUID, public_id: str) -> LegacyNote | None:
        return self.db.execute(
            select(LegacyNote).where(
                LegacyNote.owner_id == owner_id,
                LegacyNote.public_id == public_id,
                LegacyNote.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def create_memory(self, memory: LegacyMemory) -> LegacyMemory:
        self.db.add(memory)
        return memory

    def list_memories(self, owner_id: uuid.UUID) -> list[LegacyMemory]:
        return list(
            self.db.execute(
                select(LegacyMemory)
                .where(LegacyMemory.owner_id == owner_id, LegacyMemory.is_deleted.is_(False))
                .order_by(LegacyMemory.created_at.desc())
            ).scalars()
        )

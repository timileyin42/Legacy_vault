import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.verification.models import DeathVerification, Witness


class VerificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, verification: DeathVerification) -> DeathVerification:
        self.db.add(verification)
        return verification

    def list_for_owner(self, owner_id: uuid.UUID) -> list[DeathVerification]:
        return list(
            self.db.execute(
                select(DeathVerification)
                .where(DeathVerification.owner_id == owner_id, DeathVerification.is_deleted.is_(False))
                .order_by(DeathVerification.created_at.desc())
            ).scalars()
        )

    def get_for_owner(self, owner_id: uuid.UUID, public_id: str) -> DeathVerification | None:
        return self.db.execute(
            select(DeathVerification).where(
                DeathVerification.owner_id == owner_id,
                DeathVerification.public_id == public_id,
                DeathVerification.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def latest_for_owner(self, owner_id: uuid.UUID) -> DeathVerification | None:
        return self.db.execute(
            select(DeathVerification)
            .where(DeathVerification.owner_id == owner_id, DeathVerification.is_deleted.is_(False))
            .order_by(DeathVerification.created_at.desc())
        ).scalars().first()

    def add_witness(self, witness: Witness) -> Witness:
        self.db.add(witness)
        return witness

    def list_witnesses(self, verification_id: uuid.UUID) -> list[Witness]:
        return list(
            self.db.execute(
                select(Witness)
                .where(Witness.verification_id == verification_id, Witness.is_deleted.is_(False))
                .order_by(Witness.created_at.asc())
            ).scalars()
        )

    def get_witness(self, verification_id: uuid.UUID, public_id: str) -> Witness | None:
        return self.db.execute(
            select(Witness).where(
                Witness.verification_id == verification_id,
                Witness.public_id == public_id,
                Witness.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

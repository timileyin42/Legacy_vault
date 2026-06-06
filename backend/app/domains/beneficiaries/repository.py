import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.domains.beneficiaries.models import Beneficiary, TrustedContact


class BeneficiaryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, beneficiary: Beneficiary) -> Beneficiary:
        self.db.add(beneficiary)
        return beneficiary

    def list_for_owner(self, owner_id: uuid.UUID) -> list[Beneficiary]:
        return list(
            self.db.execute(
                select(Beneficiary)
                .where(Beneficiary.owner_id == owner_id, Beneficiary.is_deleted.is_(False))
                .order_by(Beneficiary.created_at.desc())
            ).scalars()
        )

    def get_for_owner(self, owner_id: uuid.UUID, public_id: str) -> Beneficiary | None:
        return self.db.execute(
            select(Beneficiary).where(
                Beneficiary.owner_id == owner_id,
                Beneficiary.public_id == public_id,
                Beneficiary.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def count_for_owner(self, owner_id: uuid.UUID) -> int:
        return self.db.execute(
            select(func.count()).select_from(Beneficiary).where(
                Beneficiary.owner_id == owner_id,
                Beneficiary.is_deleted.is_(False),
            )
        ).scalar_one()

    def total_allocation(self, owner_id: uuid.UUID) -> int:
        return int(
            self.db.execute(
                select(func.coalesce(func.sum(Beneficiary.allocation_percent), 0)).where(
                    Beneficiary.owner_id == owner_id,
                    Beneficiary.is_deleted.is_(False),
                )
            ).scalar_one()
        )


class TrustedContactRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, contact: TrustedContact) -> TrustedContact:
        self.db.add(contact)
        return contact

    def list_for_owner(self, owner_id: uuid.UUID) -> list[TrustedContact]:
        return list(
            self.db.execute(
                select(TrustedContact)
                .where(TrustedContact.owner_id == owner_id, TrustedContact.is_deleted.is_(False))
                .order_by(TrustedContact.created_at.desc())
            ).scalars()
        )

    def get_for_owner(self, owner_id: uuid.UUID, public_id: str) -> TrustedContact | None:
        return self.db.execute(
            select(TrustedContact).where(
                TrustedContact.owner_id == owner_id,
                TrustedContact.public_id == public_id,
                TrustedContact.is_deleted.is_(False),
            )
        ).scalar_one_or_none()


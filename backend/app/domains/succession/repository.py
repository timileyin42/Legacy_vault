import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.succession.models import SuccessionReport


class SuccessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, report: SuccessionReport) -> SuccessionReport:
        self.db.add(report)
        return report

    def list_for_owner(self, owner_id: uuid.UUID) -> list[SuccessionReport]:
        return list(
            self.db.execute(
                select(SuccessionReport)
                .where(SuccessionReport.owner_id == owner_id, SuccessionReport.is_deleted.is_(False))
                .order_by(SuccessionReport.created_at.desc())
            ).scalars()
        )

    def get_for_owner(self, owner_id: uuid.UUID, public_id: str) -> SuccessionReport | None:
        return self.db.execute(
            select(SuccessionReport).where(
                SuccessionReport.owner_id == owner_id,
                SuccessionReport.public_id == public_id,
                SuccessionReport.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

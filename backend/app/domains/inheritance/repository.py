import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.inheritance.models import AccessRequest, InheritanceRule


class InheritanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_rule(self, rule: InheritanceRule) -> InheritanceRule:
        self.db.add(rule)
        return rule

    def list_rules(self, owner_id: uuid.UUID) -> list[InheritanceRule]:
        return list(
            self.db.execute(
                select(InheritanceRule)
                .where(InheritanceRule.owner_id == owner_id, InheritanceRule.is_deleted.is_(False))
                .order_by(InheritanceRule.created_at.desc())
            ).scalars()
        )

    def get_rule(self, owner_id: uuid.UUID, public_id: str) -> InheritanceRule | None:
        return self.db.execute(
            select(InheritanceRule).where(
                InheritanceRule.owner_id == owner_id,
                InheritanceRule.public_id == public_id,
                InheritanceRule.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def create_access_request(self, request: AccessRequest) -> AccessRequest:
        self.db.add(request)
        return request

    def list_access_requests(self, owner_id: uuid.UUID) -> list[AccessRequest]:
        return list(
            self.db.execute(
                select(AccessRequest)
                .where(AccessRequest.owner_id == owner_id, AccessRequest.is_deleted.is_(False))
                .order_by(AccessRequest.created_at.desc())
            ).scalars()
        )

    def get_access_request(self, owner_id: uuid.UUID, public_id: str) -> AccessRequest | None:
        return self.db.execute(
            select(AccessRequest).where(
                AccessRequest.owner_id == owner_id,
                AccessRequest.public_id == public_id,
                AccessRequest.is_deleted.is_(False),
            )
        ).scalar_one_or_none()


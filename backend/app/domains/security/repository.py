from sqlalchemy.orm import Session

from backend.app.domains.security.models import AuditAction, AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        actor_id=None,
        resource_public_id: str | None = None,
        metadata_json: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_public_id=resource_public_id,
            metadata_json=metadata_json or {},
        )
        self.db.add(log)
        return log


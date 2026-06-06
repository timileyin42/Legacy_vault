from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.identity.models import UserSession
from backend.app.domains.security.models import AuditLog

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/audit-logs")
def audit_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logs = list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.actor_id == current_user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        ).scalars()
    )
    return success_response(
        "Audit logs retrieved.",
        [
            {
                "id": str(log.id),
                "action": log.action.value,
                "resource_type": log.resource_type,
                "resource_id": log.resource_public_id,
                "created_at": log.created_at.isoformat(),
                "metadata": log.metadata_json,
            }
            for log in logs
        ],
    )


@router.get("/login-history")
def login_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = list(
        db.execute(
            select(UserSession)
            .where(UserSession.user_id == current_user.id, UserSession.is_deleted.is_(False))
            .order_by(UserSession.created_at.desc())
            .limit(25)
        ).scalars()
    )
    return success_response(
        "Login history retrieved.",
        [
            {
                "id": str(session.id),
                "device_fingerprint": session.device_fingerprint,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "revoked": session.revoked_at is not None,
            }
            for session in sessions
        ],
    )

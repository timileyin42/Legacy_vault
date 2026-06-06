import uuid

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.domains.identity.models import User
from backend.app.domains.identity.repository import UserRepository

# OAuth2 password flow so the Swagger "Authorize" padlock logs in via our own
# /auth/token endpoint (email + password) and reuses the returned JWT as a Bearer
# token. auto_error=False keeps our own 401 messages.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def get_request_context(
    x_forwarded_for: str | None = Header(default=None),
    user_agent: str | None = Header(default=None),
) -> dict[str, str | None]:
    ip_address = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None
    return {"ip_address": ip_address, "user_agent": user_agent}


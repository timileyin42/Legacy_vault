from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.identity.models import (
    EmailVerificationCode,
    PasswordResetCode,
    User,
    UserSession,
)


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(
            select(User).where(User.email == email.lower(), User.is_deleted.is_(False))
        ).scalar_one_or_none()

    def get_by_id(self, user_id) -> User | None:
        return self.db.execute(
            select(User).where(User.id == user_id, User.is_deleted.is_(False))
        ).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.db.add(user)
        return user


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: UserSession) -> UserSession:
        self.db.add(session)
        return session

    def get_active_by_hash(self, refresh_token_hash: str) -> UserSession | None:
        return self.db.execute(
            select(UserSession).where(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.now(UTC),
                UserSession.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def list_for_user(self, user_id) -> list[UserSession]:
        return list(
            self.db.execute(
                select(UserSession)
                .where(UserSession.user_id == user_id, UserSession.is_deleted.is_(False))
                .order_by(UserSession.created_at.desc())
            ).scalars()
        )

    def get_for_user(self, user_id, public_id: str) -> UserSession | None:
        return self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.public_id == public_id,
                UserSession.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def revoke(self, session: UserSession) -> None:
        session.revoked_at = datetime.now(UTC)

    def revoke_all_for_user(self, user_id, except_hash: str | None = None) -> int:
        revoked = 0
        for session in self.list_for_user(user_id):
            if session.revoked_at is not None:
                continue
            if except_hash and session.refresh_token_hash == except_hash:
                continue
            session.revoked_at = datetime.now(UTC)
            revoked += 1
        return revoked


class EmailVerificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, code: EmailVerificationCode) -> EmailVerificationCode:
        self.db.add(code)
        return code

    def active_for_user(self, user_id) -> list[EmailVerificationCode]:
        return list(
            self.db.execute(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.user_id == user_id,
                    EmailVerificationCode.consumed_at.is_(None),
                    EmailVerificationCode.expires_at > datetime.now(UTC),
                )
            ).scalars()
        )


class PasswordResetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, code: PasswordResetCode) -> PasswordResetCode:
        self.db.add(code)
        return code

    def active_for_user(self, user_id) -> list[PasswordResetCode]:
        return list(
            self.db.execute(
                select(PasswordResetCode).where(
                    PasswordResetCode.user_id == user_id,
                    PasswordResetCode.consumed_at.is_(None),
                    PasswordResetCode.expires_at > datetime.now(UTC),
                )
            ).scalars()
        )


import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.domains.notifications.models import DeviceToken, Notification


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ----- Device tokens -----

    def get_token_by_hash(self, token_hash: str) -> DeviceToken | None:
        return self.db.execute(
            select(DeviceToken).where(
                DeviceToken.token_hash == token_hash, DeviceToken.is_deleted.is_(False)
            )
        ).scalar_one_or_none()

    def create_token(self, token: DeviceToken) -> DeviceToken:
        self.db.add(token)
        return token

    def list_tokens(self, owner_id: uuid.UUID) -> list[DeviceToken]:
        return list(
            self.db.execute(
                select(DeviceToken)
                .where(
                    DeviceToken.owner_id == owner_id,
                    DeviceToken.active.is_(True),
                    DeviceToken.is_deleted.is_(False),
                )
                .order_by(DeviceToken.created_at.desc())
            ).scalars()
        )

    # ----- Notifications -----

    def create_notification(self, notification: Notification) -> Notification:
        self.db.add(notification)
        return notification

    def list_notifications(self, owner_id: uuid.UUID, limit: int = 50) -> list[Notification]:
        return list(
            self.db.execute(
                select(Notification)
                .where(Notification.owner_id == owner_id, Notification.is_deleted.is_(False))
                .order_by(Notification.created_at.desc())
                .limit(limit)
            ).scalars()
        )

    def get_notification(self, owner_id: uuid.UUID, public_id: str) -> Notification | None:
        return self.db.execute(
            select(Notification).where(
                Notification.owner_id == owner_id,
                Notification.public_id == public_id,
                Notification.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def unread_count(self, owner_id: uuid.UUID) -> int:
        return self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.owner_id == owner_id,
                Notification.is_deleted.is_(False),
                Notification.read_at.is_(None),
            )
        ).scalar_one()

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService, hash_token
from backend.app.domains.identity.models import User
from backend.app.domains.notifications.models import (
    DeviceToken,
    Notification,
    NotificationCategory,
)
from backend.app.domains.notifications.repository import NotificationRepository
from backend.app.domains.notifications.schemas import (
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
    NotificationListResponse,
    NotificationResponse,
)
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.integrations.push import FcmPushClient, PushResult

# Maps a notification category to the user preference flag that gates push delivery.
_CATEGORY_PREFERENCE = {
    NotificationCategory.security_alert: "security_logs",
    NotificationCategory.inheritance_event: "inheritance_events",
    NotificationCategory.access_request: "inheritance_events",
    NotificationCategory.document: "inheritance_events",
    NotificationCategory.system: "product_updates",
}


class NotificationService:
    def __init__(self, db: Session, push_client: FcmPushClient | None = None) -> None:
        self.db = db
        self.repository = NotificationRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)
        self.push = push_client or FcmPushClient()

    def register_device(self, owner: User, request: DeviceTokenRegisterRequest) -> DeviceTokenResponse:
        token_hash = hash_token(request.token)
        existing = self.repository.get_token_by_hash(token_hash)
        if existing:
            existing.owner_id = owner.id
            existing.platform = request.platform
            existing.active = True
            existing.last_seen_at = datetime.now(UTC)
            existing.updated_by = owner.id
            device = existing
        else:
            device = DeviceToken(
                owner_id=owner.id,
                token_hash=token_hash,
                token_encrypted=self.encryption.encrypt(request.token),
                platform=request.platform,
                last_seen_at=datetime.now(UTC),
                created_by=owner.id,
                updated_by=owner.id,
            )
            self.repository.create_token(device)
        self.db.flush()
        self.audit.record(
            action=AuditAction.device_registered,
            actor_id=owner.id,
            resource_type="device_token",
            resource_public_id=device.public_id,
        )
        return self._to_device_response(device)

    def list_devices(self, owner: User) -> list[DeviceTokenResponse]:
        return [self._to_device_response(token) for token in self.repository.list_tokens(owner.id)]

    def list_notifications(self, owner: User) -> NotificationListResponse:
        items = [self._to_notification_response(n) for n in self.repository.list_notifications(owner.id)]
        return NotificationListResponse(unread_count=self.repository.unread_count(owner.id), items=items)

    def mark_read(self, owner: User, public_id: str) -> NotificationResponse:
        notification = self.repository.get_notification(owner.id, public_id)
        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
        return self._to_notification_response(notification)

    def mark_all_read(self, owner: User) -> dict:
        marked = 0
        for notification in self.repository.list_notifications(owner.id):
            if notification.read_at is None:
                notification.read_at = datetime.now(UTC)
                marked += 1
        return {"marked_read": marked}

    def notify(
        self,
        owner: User,
        *,
        category: NotificationCategory,
        title: str,
        body: str,
        metadata: dict | None = None,
    ) -> Notification:
        """Persist an in-app notification and push to the owner's devices when allowed.

        Used by other domains (security alerts, access-request updates, etc.). The
        in-app record is always written; push delivery is gated by user preferences
        and by whether ``FCM_SERVER_KEY`` is configured.
        """
        notification = Notification(
            owner_id=owner.id,
            category=category,
            title=title,
            body=body,
            metadata_json=metadata or {},
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_notification(notification)
        self.db.flush()
        if self._push_allowed(owner, category):
            self._send_push(owner, title=title, body=body, data={"category": category.value})
        return notification

    def _push_allowed(self, owner: User, category: NotificationCategory) -> bool:
        preferences = owner.notification_preferences or {}
        key = _CATEGORY_PREFERENCE.get(category)
        if key is None:
            return True
        return bool(preferences.get(key, True))

    def _send_push(self, owner: User, *, title: str, body: str, data: dict) -> PushResult:
        tokens = [self.encryption.decrypt(t.token_encrypted) for t in self.repository.list_tokens(owner.id)]
        return self.push.send_to_tokens(tokens=tokens, title=title, body=body, data=data)

    def _to_device_response(self, token: DeviceToken) -> DeviceTokenResponse:
        return DeviceTokenResponse(
            id=token.public_id,
            platform=token.platform,
            active=token.active,
            last_seen_at=token.last_seen_at.isoformat() if token.last_seen_at else None,
        )

    def _to_notification_response(self, notification: Notification) -> NotificationResponse:
        return NotificationResponse(
            id=notification.public_id,
            category=notification.category,
            title=notification.title,
            body=notification.body,
            metadata=notification.metadata_json or {},
            read=notification.read_at is not None,
            created_at=notification.created_at.isoformat(),
        )

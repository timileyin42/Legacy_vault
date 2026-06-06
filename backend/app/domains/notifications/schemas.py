from pydantic import BaseModel, Field

from backend.app.domains.notifications.models import DevicePlatform, NotificationCategory


class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    platform: DevicePlatform = DevicePlatform.ios


class DeviceTokenResponse(BaseModel):
    id: str
    platform: DevicePlatform
    active: bool
    last_seen_at: str | None


class NotificationResponse(BaseModel):
    id: str
    category: NotificationCategory
    title: str
    body: str
    metadata: dict
    read: bool
    created_at: str


class NotificationListResponse(BaseModel):
    unread_count: int
    items: list[NotificationResponse]

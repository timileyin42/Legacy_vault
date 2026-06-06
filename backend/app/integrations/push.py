"""Firebase Cloud Messaging (FCM) push delivery via the HTTP v1 API.

The legacy ``key=<server_key>`` API was deprecated by Google (and shut down in
2024), so this uses the modern **HTTP v1** flow: a Firebase service-account
credential mints a short-lived OAuth2 access token, which authorises sends to
``/v1/projects/<project_id>/messages:send``.

The service account is supplied as base64-encoded JSON via
``FCM_SERVICE_ACCOUNT_BASE64`` (keeps the secret out of the repo and works in
any deploy target). When it is not configured the client degrades gracefully and
reports the send as skipped, so local/test environments never fail on a missing
credential. v1 sends to one device token per request, so we iterate and count
successful deliveries.
"""

import base64
import json
from dataclasses import dataclass

import httpx

from backend.app.core.config import Settings, get_settings

FCM_V1_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


@dataclass(frozen=True)
class PushResult:
    delivered: int
    skipped: bool
    reason: str | None = None


class FcmPushClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.fcm_service_account_base64 and self.settings.firebase_project_id)

    def send_to_tokens(
        self,
        *,
        tokens: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> PushResult:
        if not tokens:
            return PushResult(delivered=0, skipped=True, reason="no_registered_devices")
        if not self.is_configured:
            # No service account: persist the in-app notification but skip push delivery.
            return PushResult(delivered=0, skipped=True, reason="fcm_not_configured")

        access_token = self._access_token()
        url = FCM_V1_ENDPOINT.format(project_id=self.settings.firebase_project_id)
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        # FCM v1 requires all data values to be strings.
        string_data = {str(key): str(value) for key, value in (data or {}).items()}

        delivered = 0
        with httpx.Client(timeout=10) as client:
            for device_token in tokens:
                response = client.post(
                    url,
                    headers=headers,
                    json={
                        "message": {
                            "token": device_token,
                            "notification": {"title": title, "body": body},
                            "data": string_data,
                        }
                    },
                )
                if response.status_code == 200:
                    delivered += 1
                # A non-200 (e.g. UNREGISTERED) means a stale token; it is skipped rather than retried.
        return PushResult(delivered=delivered, skipped=False)

    def _access_token(self) -> str:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        info = json.loads(base64.b64decode(self.settings.fcm_service_account_base64))
        credentials = service_account.Credentials.from_service_account_info(info, scopes=[FCM_SCOPE])
        credentials.refresh(Request())
        return credentials.token


def get_push_client() -> FcmPushClient:
    return FcmPushClient()

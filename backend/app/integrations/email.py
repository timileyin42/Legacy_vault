import logging
from dataclasses import dataclass

import httpx

from backend.app.core.config import Settings, get_settings
from backend.app.integrations import email_templates

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str | None = None


class ResendEmailClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.resend_api_key)

    def send(self, message: EmailMessage) -> dict:
        if not self.is_configured:
            # No RESEND_API_KEY: skip delivery gracefully so flows still work locally/in tests.
            return {"skipped": True, "reason": "resend_not_configured"}
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {self.settings.resend_api_key}"},
            json={
                "from": self.settings.resend_from_email,
                "to": [message.to],
                "subject": message.subject,
                "html": message.html,
                "text": message.text,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()


def get_email_client() -> ResendEmailClient:
    return ResendEmailClient()


def safe_send(client: ResendEmailClient, message: EmailMessage) -> dict:
    """Send without ever propagating a delivery failure.

    Used for non-critical notification emails (welcome, security alert, heir
    designation) dispatched as background tasks, so a Resend outage can never
    fail the core request that triggered them. Only the recipient and subject
    are logged on failure -- never the email body.
    """
    try:
        return client.send(message)
    except Exception as exc:  # noqa: BLE001 - delivery must not break the request
        logger.warning("Email delivery failed to=%s subject=%s error=%s", message.to, message.subject, exc)
        return {"skipped": True, "reason": "delivery_error"}


def build_welcome_email(*, to: str, full_name: str) -> EmailMessage:
    subject, html, text = email_templates.welcome_email(full_name)
    return EmailMessage(to=to, subject=subject, html=html, text=text)


def build_security_alert_email(
    *, to: str, full_name: str, device: str | None, ip_address: str | None, timestamp: str
) -> EmailMessage:
    subject, html, text = email_templates.security_alert_email(full_name, device, ip_address, timestamp)
    return EmailMessage(to=to, subject=subject, html=html, text=text)


def build_heir_designation_email(*, to: str, heir_name: str, owner_name: str) -> EmailMessage:
    subject, html, text = email_templates.heir_designation_email(heir_name, owner_name)
    return EmailMessage(to=to, subject=subject, html=html, text=text)


def build_verification_code_email(*, to: str, full_name: str, code: str, ttl_minutes: int) -> EmailMessage:
    subject, html, text = email_templates.verification_code_email(full_name, code, ttl_minutes)
    return EmailMessage(to=to, subject=subject, html=html, text=text)


def build_password_reset_email(*, to: str, full_name: str, code: str, ttl_minutes: int) -> EmailMessage:
    subject, html, text = email_templates.password_reset_email(full_name, code, ttl_minutes)
    return EmailMessage(to=to, subject=subject, html=html, text=text)

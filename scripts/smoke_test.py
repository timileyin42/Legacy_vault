"""End-to-end smoke test against the real (Neon) database.

Runs the whole API surface in-process with the FastAPI TestClient pointed at the
configured DATABASE_URL. External side-effects are bypassed so it costs nothing:

  * Email   -> a capturing client (no Resend send). The verification / password-
               reset flows are exercised by reading the 6-digit code straight out
               of the captured email body instead of mailing a real address.
  * Push    -> FCM send is monkeypatched to a no-op (no Google call).
  * Storage -> a fake R2 client (no Cloudflare call).

Usage:  .venv/bin/python scripts/smoke_test.py
Exits non-zero if any endpoint check fails. Creates a uniquely-emailed throwaway
user per run.
"""

import re
import sys
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.core.security import generate_totp_code
from backend.app.domains.identity.models import User, UserRole
from backend.app.integrations import push as push_mod
from backend.app.integrations.email import EmailMessage, get_email_client
from backend.app.integrations.paystack import InitResult as PaystackInit
from backend.app.integrations.paystack import VerifyResult as PaystackVerify
from backend.app.integrations.paystack import get_paystack_client
from backend.app.integrations.storage import StoredObject, get_storage_client
from backend.app.main import create_app

# ---- Bypass external side-effects ----------------------------------------------------
push_mod.FcmPushClient.send_to_tokens = lambda self, **kw: push_mod.PushResult(0, True, "smoke-bypass")


class CapturingEmail:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> dict:
        self.messages.append(message)
        return {"id": "smoke"}

    def last_code(self) -> str:
        return re.search(r"\b(\d{6})\b", self.messages[-1].text).group(1)


@dataclass
class FakeStorage:
    def upload_document(self, *, owner_public_id: str, file: UploadFile) -> StoredObject:
        payload = file.file.read()
        return StoredObject("cloudflare_r2", "smoke", f"documents/{owner_public_id}/x.pdf", "deadbeef" * 4, len(payload), file.content_type or "application/octet-stream")

    def create_presigned_read_url(self, *, object_key: str) -> str:
        return f"https://r2.example.test/{object_key}"


class FakePaystack:
    def initialize_transaction(self, *, email, amount_minor, reference, currency, callback_url, metadata) -> PaystackInit:
        return PaystackInit(f"https://checkout.paystack.com/{reference}", "acc_smoke", reference)

    def verify_transaction(self, reference: str) -> PaystackVerify:
        return PaystackVerify("success", reference, 490000, "NGN", True, {})

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        return signature == "valid-sig"


emails = CapturingEmail()
app = create_app()
app.dependency_overrides[get_email_client] = lambda: emails
app.dependency_overrides[get_storage_client] = lambda: FakeStorage()
app.dependency_overrides[get_paystack_client] = lambda: FakePaystack()
client = TestClient(app)

PASS, FAIL = 0, 0
TOKEN: str | None = None


def check(label: str, method: str, path: str, *, expect=200, auth=True, want_pdf=False, **kw):
    global PASS, FAIL
    headers = kw.pop("headers", {})
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    resp = client.request(method, path, headers=headers, **kw)
    ok_status = resp.status_code in (expect if isinstance(expect, (list, tuple)) else [expect])
    ok = ok_status and (resp.content[:5] == b"%PDF-" if want_pdf else True)
    mark = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
    detail = "pdf" if want_pdf else (resp.text[:90] if not ok else "")
    print(f"  [{mark}] {method:6} {path:48} -> {resp.status_code} {detail}")
    if want_pdf:
        return None
    try:
        return resp.json().get("data")
    except Exception:
        return None


def section(name: str):
    print(f"\n=== {name} ===")


email = f"smoke_{uuid.uuid4().hex[:10]}@example.com"
password = "smoke-secure-password-1"

section("Auth & profile")
data = check("register", "POST", "/api/v1/auth/register", auth=False,
             json={"email": email, "full_name": "Smoke Tester", "password": password, "device_fingerprint": "smoke"})
TOKEN = data["tokens"]["access_token"]
refresh_token = data["tokens"]["refresh_token"]

# Swagger OAuth2 password-flow token endpoint
form = client.post("/api/v1/auth/token", data={"username": email, "password": password})
print(f"  [{'PASS' if form.status_code==200 and 'access_token' in form.json() else 'FAIL'}] POST   /api/v1/auth/token (swagger oauth2)            -> {form.status_code}")
PASS += 1 if form.status_code == 200 else 0
FAIL += 0 if form.status_code == 200 else 1

check("login", "POST", "/api/v1/auth/login", auth=False, json={"email": email, "password": password})
check("me", "GET", "/api/v1/auth/me")
check("profile", "GET", "/api/v1/auth/profile")
check("update profile", "PUT", "/api/v1/auth/profile", json={"full_name": "Smoke T.", "theme": "light"})
check("notif settings", "PUT", "/api/v1/auth/notification-settings", json={"product_updates": True})
check("security settings", "PUT", "/api/v1/auth/security-settings", json={"biometric_enabled": True})
check("sessions", "GET", "/api/v1/auth/sessions")
check("refresh", "POST", "/api/v1/auth/refresh", auth=False, json={"refresh_token": refresh_token})

section("Email verification flow (code read from captured email, no send)")
check("verification send", "POST", "/api/v1/auth/verification/send")
code = emails.last_code()
vr = check("verification confirm", "POST", "/api/v1/auth/verification/confirm", json={"code": code})
print(f"        -> email_verified={vr.get('email_verified') if vr else '?'}")

section("Password reset flow (code read from captured email, no send)")
check("forgot password", "POST", "/api/v1/auth/password/forgot", auth=False, json={"email": email})
reset_code = emails.last_code()
check("reset password", "POST", "/api/v1/auth/password/reset", auth=False,
      json={"email": email, "code": reset_code, "new_password": "smoke-secure-password-2"})
# Re-login with the new password and refresh the token for the rest of the run.
relog = check("login (new pw)", "POST", "/api/v1/auth/login", auth=False,
              json={"email": email, "password": "smoke-secure-password-2"})
TOKEN = relog["tokens"]["access_token"]

section("MFA")
setup = check("mfa setup", "POST", "/api/v1/auth/mfa/setup")
check("mfa verify", "POST", "/api/v1/auth/mfa/verify", json={"code": generate_totp_code(setup["secret"])})

section("Vault")
item = check("create item", "POST", "/api/v1/vault/items",
             json={"category": "password", "title": "Email login", "sensitive_payload": {"password": "x"}})
check("list items", "GET", "/api/v1/vault/items")
check("get item", "GET", f"/api/v1/vault/items/{item['id']}")
check("update item", "PUT", f"/api/v1/vault/items/{item['id']}", json={"title": "Email login v2"})
asset = check("create asset", "POST", "/api/v1/vault/assets",
              json={"category": "investment", "name": "Equity Trust", "value_estimate": 12450000, "currency": "USD"})
check("list assets", "GET", "/api/v1/vault/assets")
check("get asset", "GET", f"/api/v1/vault/assets/{asset['id']}")
check("update asset", "PUT", f"/api/v1/vault/assets/{asset['id']}", json={"value_estimate": 13000000})
doc = check("create document", "POST", "/api/v1/vault/documents",
            json={"title": "Will", "document_type": "will", "storage_object": "r2://b/w.pdf", "checksum": "abc123456789def0", "expires_at": "2026-07-01T00:00:00Z"})
check("list documents", "GET", "/api/v1/vault/documents")
check("doc categories", "GET", "/api/v1/vault/documents/categories")
check("doc expiring", "GET", "/api/v1/vault/documents/expiring?within_days=120")
check("get document", "GET", f"/api/v1/vault/documents/{doc['id']}")
check("doc read-url", "POST", f"/api/v1/vault/documents/{doc['id']}/read-url")
check("upload document", "POST", "/api/v1/vault/documents/upload",
      data={"title": "Deed", "document_type": "deed"}, files={"file": ("deed.pdf", b"bytes", "application/pdf")})

section("Beneficiaries & trusted contacts")
ben = check("create beneficiary", "POST", "/api/v1/beneficiaries",
            json={"full_name": "Sarah Heir", "email": "sarah@example.com", "relationship": "child", "allocation_percent": 100})
check("list beneficiaries", "GET", "/api/v1/beneficiaries")
check("allocation summary", "GET", "/api/v1/beneficiaries/summary")
check("get beneficiary", "GET", f"/api/v1/beneficiaries/{ben['id']}")
check("update beneficiary", "PUT", f"/api/v1/beneficiaries/{ben['id']}", json={"allocation_percent": 90})
check("verify beneficiary", "POST", f"/api/v1/beneficiaries/{ben['id']}/verify", json={"status": "verified"})
check("create trusted contact", "POST", "/api/v1/trusted-contacts",
      json={"full_name": "Robert Trust", "email": "robert@example.com", "phone": "+15550100"})
check("list trusted contacts", "GET", "/api/v1/trusted-contacts")

section("Inheritance engine")
rule = check("create rule", "POST", "/api/v1/inheritance/rules",
             json={"beneficiary_id": ben["id"], "trigger": "death_verification"})
check("list rules", "GET", "/api/v1/inheritance/rules")
check("distribution summary", "GET", "/api/v1/inheritance/rules/distribution-summary")
check("get rule", "GET", f"/api/v1/inheritance/rules/{rule['id']}")
check("update rule", "PUT", f"/api/v1/inheritance/rules/{rule['id']}", json={"trigger": "age_reached", "conditions": {"age": 25}})
check("toggle rule", "POST", f"/api/v1/inheritance/rules/{rule['id']}/toggle", json={"active": False})
acc = check("create access request", "POST", "/api/v1/inheritance/access-requests",
            json={"beneficiary_id": ben["id"], "request_type": "death_verification", "evidence_summary": "Death certificate submitted."})
check("list access requests", "GET", "/api/v1/inheritance/access-requests")
check("update access status", "PATCH", f"/api/v1/inheritance/access-requests/{acc['id']}/status",
      json={"status": "waiting_period", "reviewer_notes": "Accepted."})

section("Verification (death + emergency access)")
dv = check("create death verification", "POST", "/api/v1/verification/death",
           json={"certificate_file_name": "dc.pdf", "certificate_object": "r2://b/dc.pdf", "certificate_checksum": "abc123456789def0",
                 "witnesses": [{"full_name": "W One", "email": "w1@example.com"}, {"full_name": "W Two", "email": "w2@example.com"}]})
check("list death verifications", "GET", "/api/v1/verification/death")
check("get death verification", "GET", f"/api/v1/verification/death/{dv['id']}")
wid = dv["witnesses"][0]["id"]
check("witness respond", "POST", f"/api/v1/verification/death/{dv['id']}/witnesses/{wid}/respond", json={"status": "verified"})
check("update stages", "PATCH", f"/api/v1/verification/death/{dv['id']}/stages",
      json={"court_crosscheck_status": "validated", "vault_unlock_status": "validated"})
check("emergency access status", "GET", "/api/v1/verification/emergency-access")

section("Legacy / memory vault")
note = check("create note", "POST", "/api/v1/legacy/notes",
             json={"title": "Birthday Note", "body": "Happy birthday.", "media_type": "written", "release_trigger": "event"})
check("list notes", "GET", "/api/v1/legacy/notes")
check("scheduled notes", "GET", "/api/v1/legacy/notes/scheduled")
check("get note", "GET", f"/api/v1/legacy/notes/{note['id']}")
check("update note", "PUT", f"/api/v1/legacy/notes/{note['id']}", json={"title": "Final Directive"})
check("create memory", "POST", "/api/v1/legacy/memories", json={"caption": "Holiday", "storage_object": "r2://b/p.jpg", "content_type": "image/jpeg"})
check("list memories", "GET", "/api/v1/legacy/memories")

section("Analytics & AI advisor")
check("readiness", "GET", "/api/v1/analytics/readiness")
check("asset distribution", "GET", "/api/v1/analytics/asset-distribution")
check("beneficiary coverage", "GET", "/api/v1/analytics/beneficiary-coverage")
check("security metrics", "GET", "/api/v1/analytics/security-metrics")
check("trends", "GET", "/api/v1/analytics/trends")
check("recommendations", "GET", "/api/v1/ai-advisor/recommendations")
check("estate readiness", "GET", "/api/v1/ai-advisor/estate-readiness")
check("risk analysis", "GET", "/api/v1/ai-advisor/risk-analysis")
check("advisor chat", "POST", "/api/v1/ai-advisor/chat", json={"message": "How ready is my estate?"})

section("Subscriptions & Paystack")
check("plans", "GET", "/api/v1/subscriptions/plans", auth=False)
check("current", "GET", "/api/v1/subscriptions/current")
co = check("checkout (paystack init)", "POST", "/api/v1/subscriptions/checkout", json={"plan": "premium", "billing_cycle": "monthly"})
check("verify checkout", "GET", f"/api/v1/subscriptions/checkout/{co['reference']}/verify")
check("billing history", "GET", "/api/v1/subscriptions/billing-history")
check("change -> free (downgrade)", "POST", "/api/v1/subscriptions/change", json={"plan": "free"})

section("Notifications")
check("register device", "POST", "/api/v1/notifications/devices", json={"token": "fcm-token-" + uuid.uuid4().hex, "platform": "ios"})
check("list devices", "GET", "/api/v1/notifications/devices")
check("list notifications", "GET", "/api/v1/notifications")
check("mark all read", "POST", "/api/v1/notifications/read-all")

section("Succession reports")
rep = check("generate report", "POST", "/api/v1/succession-reports", json={"final_message": "Farewell."})
check("list reports", "GET", "/api/v1/succession-reports")
check("get report", "GET", f"/api/v1/succession-reports/{rep['id']}")
check("share report", "POST", f"/api/v1/succession-reports/{rep['id']}/share")
check("download pdf", "GET", f"/api/v1/succession-reports/{rep['id']}/pdf", want_pdf=True)

section("Dashboard & security center")
check("dashboard summary", "GET", "/api/v1/dashboard/summary")
check("audit logs", "GET", "/api/v1/security/audit-logs")
check("login history", "GET", "/api/v1/security/login-history")

section("Admin (after promoting the smoke user)")
with SessionLocal() as db:
    user = db.query(User).filter(User.email == email).one()
    user.role = UserRole.admin
    db.commit()
check("admin dashboard", "GET", "/api/v1/admin/dashboard")
check("admin users", "GET", "/api/v1/admin/users")
check("admin verification queue", "GET", "/api/v1/admin/verification-queue")
check("admin approve", "POST", f"/api/v1/admin/verifications/{acc['id']}/approve")

print(f"\n================  {PASS} passed, {FAIL} failed  ================")
print(f"(emails captured, not sent: {len(emails.messages)})")
sys.exit(1 if FAIL else 0)

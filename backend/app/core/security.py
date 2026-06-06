import base64
import hmac
import hashlib
import secrets
import struct
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from backend.app.core.config import get_settings


PBKDF2_ITERATIONS = 390_000


class EncryptionService:
    def __init__(self, key: str | None = None) -> None:
        raw_key = key or get_settings().encryption_key
        self._fernet = Fernet(self._normalize_key(raw_key))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Encrypted value could not be decrypted.") from exc

    @staticmethod
    def _normalize_key(key: str) -> bytes:
        try:
            Fernet(key.encode("utf-8"))
            return key.encode("utf-8")
        except Exception:
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            return base64.urlsafe_b64encode(digest)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${base64.b64encode(digest).decode('utf-8')}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        actual = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_numeric_code(length: int = 6) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def create_access_token(subject: uuid.UUID, role: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": str(subject), "role": role, "type": "access", "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: uuid.UUID, expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    raw = f"{subject}.{uuid.uuid4()}.{datetime.now(UTC).timestamp()}"
    token = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest()).decode("utf-8")
    return token, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid authentication token.") from exc
    if payload.get("type") != "access":
        raise ValueError("Invalid authentication token type.")
    return payload


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def build_totp_uri(*, issuer: str, account_name: str, secret: str) -> str:
    label = f"{issuer}:{account_name}"
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"


def generate_totp_code(secret: str, for_time: int | None = None) -> str:
    normalized_secret = secret.upper()
    padded_secret = normalized_secret + "=" * ((8 - len(normalized_secret) % 8) % 8)
    key = base64.b32decode(padded_secret)
    counter = int((for_time or time.time()) // 30)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code_int % 1_000_000:06d}"


def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    if not code.isdigit() or len(code) != 6:
        return False
    now = int(time.time())
    return any(
        hmac.compare_digest(generate_totp_code(secret, now + offset * 30), code)
        for offset in range(-window, window + 1)
    )

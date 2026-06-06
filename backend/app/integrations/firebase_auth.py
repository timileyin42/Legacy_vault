"""Firebase Authentication ID-token verification (Google / Firebase sign-in).

The Flutter app signs the user in with Google through the Firebase client SDK and
sends the resulting Firebase ID token to the backend. We verify that token here
against Google's published signing certificates and hand the verified claims to
the identity service, which finds-or-creates the user and issues our own JWTs.

This uses the same project as FCM. ``FIREBASE_PROJECT_ID`` must be set; if it is
not, the endpoint reports the feature as unconfigured rather than failing opaquely.
"""

from dataclasses import dataclass

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import HTTPException, status
from jose import JWTError, jwt

from backend.app.core.config import Settings, get_settings

GOOGLE_CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
)


@dataclass(frozen=True)
class FirebaseClaims:
    uid: str
    email: str | None
    name: str | None
    email_verified: bool


class FirebaseAuthClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.firebase_project_id)

    def verify_id_token(self, id_token: str) -> FirebaseClaims:
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google sign-in is not configured.",
            )
        project_id = self.settings.firebase_project_id
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token.") from exc

        cert_pem = self._fetch_certs().get(kid)
        if not cert_pem:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token signing key.")
        public_key_pem = (
            load_pem_x509_certificate(cert_pem.encode("utf-8"))
            .public_key()
            .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
            .decode("utf-8")
        )
        try:
            claims = jwt.decode(
                id_token,
                public_key_pem,
                algorithms=["RS256"],
                audience=project_id,
                issuer=f"https://securetoken.google.com/{project_id}",
            )
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token.") from exc

        return FirebaseClaims(
            uid=claims.get("user_id") or claims.get("sub", ""),
            email=claims.get("email"),
            name=claims.get("name") or claims.get("email"),
            email_verified=bool(claims.get("email_verified", False)),
        )

    def _fetch_certs(self) -> dict:
        response = httpx.get(GOOGLE_CERTS_URL, timeout=10)
        response.raise_for_status()
        return response.json()


def get_firebase_auth_client() -> FirebaseAuthClient:
    return FirebaseAuthClient()

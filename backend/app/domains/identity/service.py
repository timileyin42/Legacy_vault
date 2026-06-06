import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import (
    EncryptionService,
    build_totp_uri,
    create_access_token,
    create_refresh_token,
    generate_numeric_code,
    generate_totp_secret,
    hash_password,
    hash_token,
    verify_totp_code,
    verify_password,
)
from backend.app.domains.identity.models import (
    AuthProvider,
    EmailVerificationCode,
    PasswordResetCode,
    User,
    UserSession,
)
from backend.app.domains.identity.repository import (
    EmailVerificationRepository,
    PasswordResetRepository,
    SessionRepository,
    UserRepository,
)
from backend.app.domains.identity.schemas import (
    AuthResponse,
    DataExportResponse,
    LoginRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    NotificationPreferencesRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    SecuritySettingsRequest,
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.integrations.email import (
    ResendEmailClient,
    build_password_reset_email,
    build_verification_code_email,
    safe_send,
)
from backend.app.integrations.firebase_auth import FirebaseClaims


class IdentityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.email_codes = EmailVerificationRepository(db)
        self.password_resets = PasswordResetRepository(db)
        self.audit = AuditRepository(db)
        self.encryption = EncryptionService()

    def register(self, request: RegisterRequest, ip_address: str | None, user_agent: str | None) -> AuthResponse:
        if self.users.get_by_email(request.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

        user = User(
            email=request.email.lower(),
            full_name=request.full_name,
            password_hash=hash_password(request.password),
        )
        self.users.create(user)
        self.db.flush()
        self.audit.record(action=AuditAction.user_registered, actor_id=user.id, resource_type="user")
        return self._issue_auth_response(user, request.device_fingerprint, ip_address, user_agent)

    def login(self, request: LoginRequest, ip_address: str | None, user_agent: str | None) -> AuthResponse:
        user = self.users.get_by_email(request.email)
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        user.last_login_at = datetime.now(UTC)
        self.audit.record(action=AuditAction.user_login, actor_id=user.id, resource_type="user")
        return self._issue_auth_response(user, request.device_fingerprint, ip_address, user_agent)

    def refresh(self, refresh_token: str) -> TokenResponse:
        session = self.sessions.get_active_by_hash(hash_token(refresh_token))
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
        user = self.users.get_by_id(session.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
        access_token = create_access_token(user.id, user.role.value)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=get_settings().access_token_expire_minutes * 60,
        )

    def google_sign_in(
        self,
        claims: FirebaseClaims,
        device_fingerprint: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthResponse:
        if not claims.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Google account has no email address."
            )
        user = self.users.get_by_email(claims.email)
        if user is None:
            user = User(
                email=claims.email.lower(),
                full_name=claims.name or claims.email,
                # Google users authenticate via Firebase; set an unusable random password.
                password_hash=hash_password(secrets.token_urlsafe(32)),
                auth_provider=AuthProvider.google,
                firebase_uid=claims.uid,
                email_verified=claims.email_verified,
            )
            self.users.create(user)
            self.db.flush()
            self.audit.record(action=AuditAction.user_registered, actor_id=user.id, resource_type="user")
        else:
            if not user.firebase_uid:
                user.firebase_uid = claims.uid
                user.auth_provider = AuthProvider.google
            if claims.email_verified:
                user.email_verified = True
        user.last_login_at = datetime.now(UTC)
        self.audit.record(action=AuditAction.user_login, actor_id=user.id, resource_type="user")
        return self._issue_auth_response(user, device_fingerprint, ip_address, user_agent)

    def send_email_verification(self, user: User, email_client: ResendEmailClient) -> dict:
        ttl_minutes = get_settings().email_verification_code_ttl_minutes
        code = generate_numeric_code(6)
        self.email_codes.create(
            EmailVerificationCode(
                user_id=user.id,
                code_hash=hash_token(code),
                expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
            )
        )
        self.db.flush()
        delivery = email_client.send(
            build_verification_code_email(
                to=user.email, full_name=user.full_name, code=code, ttl_minutes=ttl_minutes
            )
        )
        return {"sent": not delivery.get("skipped", False), "expires_in_minutes": ttl_minutes}

    def confirm_email_verification(self, user: User, code: str) -> ProfileResponse:
        target_hash = hash_token(code)
        match = None
        for candidate in self.email_codes.active_for_user(user.id):
            if hmac.compare_digest(candidate.code_hash, target_hash):
                match = candidate
                break
        if match is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code."
            )
        match.consumed_at = datetime.now(UTC)
        user.email_verified = True
        user.updated_by = user.id
        return self._to_profile_response(user)

    def request_password_reset(self, email: str, email_client: ResendEmailClient) -> dict:
        """Send a password-reset code. Always reports success to avoid email enumeration."""
        ttl_minutes = get_settings().email_verification_code_ttl_minutes
        user = self.users.get_by_email(email)
        if user is not None:
            code = generate_numeric_code(6)
            self.password_resets.create(
                PasswordResetCode(
                    user_id=user.id,
                    code_hash=hash_token(code),
                    expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
                )
            )
            self.db.flush()
            safe_send(
                email_client,
                build_password_reset_email(
                    to=user.email, full_name=user.full_name, code=code, ttl_minutes=ttl_minutes
                ),
            )
        return {"sent": True, "expires_in_minutes": ttl_minutes}

    def reset_password(self, email: str, code: str, new_password: str) -> dict:
        invalid = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset code."
        )
        user = self.users.get_by_email(email)
        if user is None:
            raise invalid
        target_hash = hash_token(code)
        match = None
        for candidate in self.password_resets.active_for_user(user.id):
            if hmac.compare_digest(candidate.code_hash, target_hash):
                match = candidate
                break
        if match is None:
            raise invalid
        match.consumed_at = datetime.now(UTC)
        user.password_hash = hash_password(new_password)
        user.updated_by = user.id
        # Security: invalidate every existing session after a password reset.
        revoked = self.sessions.revoke_all_for_user(user.id)
        self.audit.record(
            action=AuditAction.security_settings_changed,
            actor_id=user.id,
            resource_type="user",
            metadata_json={"event": "password_reset"},
        )
        return {"reset": True, "revoked_sessions": revoked}

    def setup_mfa(self, user: User) -> MfaSetupResponse:
        secret = generate_totp_secret()
        user.mfa_secret_encrypted = self.encryption.encrypt(secret)
        user.updated_by = user.id
        return MfaSetupResponse(
            secret=secret,
            provisioning_uri=build_totp_uri(
                issuer=get_settings().mfa_issuer,
                account_name=user.email,
                secret=secret,
            ),
        )

    def verify_mfa(self, user: User, request: MfaVerifyRequest) -> UserResponse:
        if not user.mfa_secret_encrypted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA has not been set up.")
        secret = self.encryption.decrypt(user.mfa_secret_encrypted)
        if not verify_totp_code(secret, request.code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MFA code.")
        user.mfa_enabled = True
        user.updated_by = user.id
        return self.to_user_response(user)

    def _issue_auth_response(
        self,
        user: User,
        device_fingerprint: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuthResponse:
        refresh_token, expires_at = create_refresh_token(user.id)
        self.sessions.create(
            UserSession(
                user_id=user.id,
                refresh_token_hash=hash_token(refresh_token),
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
            )
        )
        access_token = create_access_token(user.id, user.role.value)
        return AuthResponse(
            user=self.to_user_response(user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=get_settings().access_token_expire_minutes * 60,
            ),
        )

    @staticmethod
    def to_user_response(user: User) -> UserResponse:
        return UserResponse(
            id=user.public_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            mfa_enabled=user.mfa_enabled,
        )

    # ----- Profile & settings -----

    def get_profile(self, user: User) -> ProfileResponse:
        return self._to_profile_response(user)

    def update_profile(self, user: User, request: ProfileUpdateRequest) -> ProfileResponse:
        if request.full_name is not None:
            user.full_name = request.full_name
        if request.phone is not None:
            user.phone_encrypted = self.encryption.encrypt(request.phone) if request.phone else None
        if request.avatar_url is not None:
            user.avatar_url = request.avatar_url or None
        if request.language is not None:
            user.language = request.language
        if request.theme is not None:
            user.theme = request.theme
        user.updated_by = user.id
        self.audit.record(action=AuditAction.profile_updated, actor_id=user.id, resource_type="user")
        return self._to_profile_response(user)

    def update_notification_preferences(
        self, user: User, request: NotificationPreferencesRequest
    ) -> ProfileResponse:
        preferences = dict(user.notification_preferences or {})
        for key, value in request.model_dump(exclude_none=True).items():
            preferences[key] = value
        user.notification_preferences = preferences
        user.updated_by = user.id
        return self._to_profile_response(user)

    def update_security_settings(self, user: User, request: SecuritySettingsRequest) -> ProfileResponse:
        if request.biometric_enabled is not None:
            user.biometric_enabled = request.biometric_enabled
        user.updated_by = user.id
        self.audit.record(
            action=AuditAction.security_settings_changed, actor_id=user.id, resource_type="user"
        )
        return self._to_profile_response(user)

    def list_sessions(self, user: User) -> list[SessionResponse]:
        return [self._to_session_response(session) for session in self.sessions.list_for_user(user.id)]

    def revoke_session(self, user: User, public_id: str) -> SessionResponse:
        session = self.sessions.get_for_user(user.id, public_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        self.sessions.revoke(session)
        self.audit.record(
            action=AuditAction.session_revoked,
            actor_id=user.id,
            resource_type="session",
            resource_public_id=session.public_id,
        )
        return self._to_session_response(session)

    def logout(self, user: User, refresh_token: str | None) -> dict:
        except_hash = None
        revoked = self.sessions.revoke_all_for_user(user.id, except_hash=except_hash)
        if refresh_token:
            target = self.sessions.get_active_by_hash(hash_token(refresh_token))
            if target:
                self.sessions.revoke(target)
        self.audit.record(action=AuditAction.user_logout, actor_id=user.id, resource_type="user")
        return {"revoked_sessions": revoked}

    def export_data(self, user: User) -> DataExportResponse:
        from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
        from backend.app.domains.vault.repository import VaultRepository

        vault = VaultRepository(self.db)
        beneficiaries = BeneficiaryRepository(self.db)
        assets = vault.list_assets(user.id)
        documents = vault.list_documents(user.id)
        heirs = beneficiaries.list_for_owner(user.id)
        return DataExportResponse(
            generated_at=datetime.now(UTC).isoformat(),
            profile=self._to_profile_response(user),
            counts={
                "vault_items": vault.count_items(user.id),
                "assets": len(assets),
                "documents": len(documents),
                "beneficiaries": len(heirs),
            },
            assets=[
                {
                    "id": asset.public_id,
                    "category": asset.category.value,
                    "name": self.encryption.decrypt(asset.name_encrypted),
                    "value_estimate": float(asset.value_estimate) if asset.value_estimate is not None else None,
                    "currency": asset.currency,
                }
                for asset in assets
            ],
            beneficiaries=[
                {
                    "id": heir.public_id,
                    "full_name": self.encryption.decrypt(heir.full_name_encrypted),
                    "email": heir.email,
                    "relationship": heir.relationship,
                    "allocation_percent": heir.allocation_percent,
                }
                for heir in heirs
            ],
            documents=[
                {
                    "id": document.public_id,
                    "title": self.encryption.decrypt(document.title_encrypted),
                    "document_type": document.document_type,
                    "classification": document.classification,
                }
                for document in documents
            ],
        )

    def _to_profile_response(self, user: User) -> ProfileResponse:
        return ProfileResponse(
            id=user.public_id,
            email=user.email,
            full_name=user.full_name,
            phone=self.encryption.decrypt(user.phone_encrypted) if user.phone_encrypted else None,
            avatar_url=user.avatar_url,
            role=user.role.value,
            auth_provider=user.auth_provider.value,
            email_verified=user.email_verified,
            mfa_enabled=user.mfa_enabled,
            biometric_enabled=user.biometric_enabled,
            language=user.language,
            theme=user.theme,
            notification_preferences=user.notification_preferences or {},
        )

    @staticmethod
    def _to_session_response(session: UserSession) -> SessionResponse:
        return SessionResponse(
            id=session.public_id,
            device_fingerprint=session.device_fingerprint,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at.isoformat(),
            expires_at=session.expires_at.isoformat(),
            revoked=session.revoked_at is not None,
        )

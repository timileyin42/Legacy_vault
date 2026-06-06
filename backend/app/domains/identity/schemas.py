from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    device_fingerprint: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    device_fingerprint: str | None = Field(default=None, max_length=255)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class GoogleSignInRequest(BaseModel):
    id_token: str = Field(min_length=16)
    device_fingerprint: str | None = Field(default=None, max_length=255)


class EmailVerificationConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=12, max_length=128)


class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MfaVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    mfa_enabled: bool


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class RefreshLogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=16)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    avatar_url: str | None = Field(default=None, max_length=512)
    language: str | None = Field(default=None, max_length=16)
    theme: str | None = Field(default=None, max_length=16)


class NotificationPreferencesRequest(BaseModel):
    inheritance_events: bool | None = None
    security_logs: bool | None = None
    product_updates: bool | None = None


class SecuritySettingsRequest(BaseModel):
    biometric_enabled: bool | None = None


class ProfileResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None
    avatar_url: str | None
    role: str
    auth_provider: str
    email_verified: bool
    mfa_enabled: bool
    biometric_enabled: bool
    language: str
    theme: str
    notification_preferences: dict


class SessionResponse(BaseModel):
    id: str
    device_fingerprint: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: str
    expires_at: str
    revoked: bool


class DataExportResponse(BaseModel):
    generated_at: str
    profile: ProfileResponse
    counts: dict
    assets: list[dict]
    beneficiaries: list[dict]
    documents: list[dict]

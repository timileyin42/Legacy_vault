from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user, get_request_context
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.identity.schemas import (
    EmailVerificationConfirmRequest,
    ForgotPasswordRequest,
    GoogleSignInRequest,
    LoginRequest,
    MfaVerifyRequest,
    NotificationPreferencesRequest,
    ProfileUpdateRequest,
    RefreshLogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SecuritySettingsRequest,
)
from backend.app.domains.identity.service import IdentityService
from backend.app.integrations.email import (
    ResendEmailClient,
    build_password_reset_email,
    build_security_alert_email,
    build_welcome_email,
    get_email_client,
    safe_send,
)
from backend.app.integrations.firebase_auth import FirebaseAuthClient, get_firebase_auth_client

router = APIRouter(prefix="/auth", tags=["Identity"])


@router.post("/register")
def register(
    request: RegisterRequest,
    background: BackgroundTasks,
    context: dict = Depends(get_request_context),
    email_client: ResendEmailClient = Depends(get_email_client),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).register(request, context["ip_address"], context["user_agent"])
    db.commit()
    # Welcome email is best-effort: dispatched after the response, never fails registration.
    background.add_task(
        safe_send, email_client, build_welcome_email(to=response.user.email, full_name=response.user.full_name)
    )
    return success_response("Registration successful.", response.model_dump())


@router.post("/login")
def login(
    request: LoginRequest,
    background: BackgroundTasks,
    context: dict = Depends(get_request_context),
    email_client: ResendEmailClient = Depends(get_email_client),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).login(request, context["ip_address"], context["user_agent"])
    db.commit()
    background.add_task(
        safe_send,
        email_client,
        build_security_alert_email(
            to=response.user.email,
            full_name=response.user.full_name,
            device=request.device_fingerprint,
            ip_address=context["ip_address"],
            timestamp=datetime.now(UTC).strftime("%B %d, %Y at %H:%M UTC"),
        ),
    )
    return success_response("Login successful.", response.model_dump())


@router.post("/token", include_in_schema=False)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    context: dict = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """OAuth2 password-flow token endpoint powering the Swagger 'Authorize' padlock.

    Accepts the standard form fields (``username`` = email, ``password``) and
    returns ``{access_token, token_type}``. Backed by the same login service as
    /auth/login so Swagger uses our real credentials.
    """
    login_request = LoginRequest(email=form_data.username, password=form_data.password)
    response = IdentityService(db).login(login_request, context["ip_address"], context["user_agent"])
    db.commit()
    return {"access_token": response.tokens.access_token, "token_type": "bearer"}


@router.post("/refresh")
def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    response = IdentityService(db).refresh(request.refresh_token)
    return success_response("Token refreshed.", response.model_dump())


@router.post("/google")
def google_sign_in(
    request: GoogleSignInRequest,
    context: dict = Depends(get_request_context),
    firebase: FirebaseAuthClient = Depends(get_firebase_auth_client),
    db: Session = Depends(get_db),
):
    claims = firebase.verify_id_token(request.id_token)
    response = IdentityService(db).google_sign_in(
        claims, request.device_fingerprint, context["ip_address"], context["user_agent"]
    )
    db.commit()
    return success_response("Google sign-in successful.", response.model_dump())


@router.post("/password/forgot")
def forgot_password(
    request: ForgotPasswordRequest,
    email_client: ResendEmailClient = Depends(get_email_client),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).request_password_reset(request.email, email_client)
    db.commit()
    # Generic success regardless of whether the email exists (no account enumeration).
    return success_response("If the account exists, a reset code has been sent.", response)


@router.post("/password/reset")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    response = IdentityService(db).reset_password(request.email, request.code, request.new_password)
    db.commit()
    return success_response("Password reset successful.", response)


@router.post("/verification/send")
def send_email_verification(
    current_user: User = Depends(get_current_user),
    email_client: ResendEmailClient = Depends(get_email_client),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).send_email_verification(current_user, email_client)
    db.commit()
    return success_response("Verification code sent.", response)


@router.post("/verification/confirm")
def confirm_email_verification(
    request: EmailVerificationConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).confirm_email_verification(current_user, request.code)
    db.commit()
    return success_response("Email verified.", response.model_dump())


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response("Current user retrieved.", IdentityService.to_user_response(current_user).model_dump())


@router.post("/mfa/setup")
def setup_mfa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = IdentityService(db).setup_mfa(current_user)
    db.commit()
    return success_response("MFA setup started.", response.model_dump())


@router.post("/mfa/verify")
def verify_mfa(
    request: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).verify_mfa(current_user, request)
    db.commit()
    return success_response("MFA enabled.", response.model_dump())


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = IdentityService(db).get_profile(current_user)
    return success_response("Profile retrieved.", response.model_dump())


@router.put("/profile")
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).update_profile(current_user, request)
    db.commit()
    return success_response("Profile updated.", response.model_dump())


@router.put("/notification-settings")
def update_notification_settings(
    request: NotificationPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).update_notification_preferences(current_user, request)
    db.commit()
    return success_response("Notification settings updated.", response.model_dump())


@router.put("/security-settings")
def update_security_settings(
    request: SecuritySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).update_security_settings(current_user, request)
    db.commit()
    return success_response("Security settings updated.", response.model_dump())


@router.get("/sessions")
def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = IdentityService(db).list_sessions(current_user)
    return success_response("Sessions retrieved.", [item.model_dump() for item in response])


@router.post("/sessions/{public_id}/revoke")
def revoke_session(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = IdentityService(db).revoke_session(current_user, public_id)
    db.commit()
    return success_response("Session revoked.", response.model_dump())


@router.post("/logout")
def logout(
    request: RefreshLogoutRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    refresh_token = request.refresh_token if request else None
    response = IdentityService(db).logout(current_user, refresh_token)
    db.commit()
    return success_response("Logged out.", response)


@router.post("/export")
def export_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = IdentityService(db).export_data(current_user)
    return success_response("Data export generated.", response.model_dump())

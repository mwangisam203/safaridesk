from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenRefreshRequest,
    TokenResponse,
    VerificationResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    login_user,
    login_user_by_email,
    get_password_reset_recipient,
    get_verification_recipient,
    refresh_user_tokens,
    register_user,
    reset_user_password,
    send_password_reset_for_user,
    send_verification_for_user,
    verify_user_email,
)
from app.services.email_service import send_test_email
from app.core.dependencies import get_current_user
from app.core.rate_limit import rate_limit
from app.models.user import User

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("auth:register", limit=5, window_seconds=3600))],
)
def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Register a new user. Sends verification email."""
    user = register_user(request, db, send_verification=False)
    background_tasks.add_task(send_verification_for_user, user.id)
    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth:login", limit=10, window_seconds=300))],
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password. Returns JWT tokens."""
    return login_user(request, db)

@router.post(
    "/token",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth:token", limit=10, window_seconds=300))],
)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 login for the Swagger Authorize button. Use email as username."""
    return login_user_by_email(form_data.username, form_data.password, db)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Rotate a valid refresh token into a new access and refresh token pair."""
    return refresh_user_tokens(request.refresh_token, db)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get currently logged in user's profile."""
    return current_user

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout. Client should delete the token."""
    # With JWT, logout is handled client-side (delete the token)
    # For proper server-side logout, add token to a Redis blacklist
    return {"message": "Logged out successfully"}


@router.get("/verify-email", response_model=VerificationResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    user = verify_user_email(token, db)
    return VerificationResponse(
        message="Email verified successfully.",
        is_verified=user.is_verified,
    )


@router.post(
    "/resend-verification",
    response_model=VerificationResponse,
    dependencies=[Depends(rate_limit("auth:resend-verification", limit=6, window_seconds=900))],
)
def resend_verification(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    if current_user.is_verified:
        return VerificationResponse(
            message="Email is already verified.",
            is_verified=True,
        )
    background_tasks.add_task(send_verification_for_user, current_user.id)
    return VerificationResponse(
        message="Verification email sent.",
        is_verified=False,
    )


@router.post(
    "/resend-verification-email",
    response_model=VerificationResponse,
    dependencies=[Depends(rate_limit("auth:resend-verification-email", limit=6, window_seconds=900))],
)
def resend_verification_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_verification_recipient(request.email, db)
    if user:
        background_tasks.add_task(send_verification_for_user, user.id)
    return VerificationResponse(
        message="If this account exists and is not verified, a verification email has been sent.",
        is_verified=False,
    )


@router.post(
    "/forgot-password",
    dependencies=[Depends(rate_limit("auth:forgot-password", limit=5, window_seconds=900))],
)
def forgot_password(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_password_reset_recipient(request.email, db)
    if user:
        background_tasks.add_task(send_password_reset_for_user, user.id)
    return {
        "message": "If this account exists, a password reset email has been sent."
    }


@router.post("/reset-password")
def reset_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    reset_user_password(request.token, request.password, db)
    return {"message": "Password reset successfully. You can now sign in."}


@router.post("/test-email")
def test_email(to_email: str):
    """Send a test email to Mailtrap."""
    send_test_email(to_email)
    return {"message": "Test email sent"}

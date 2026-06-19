import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
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
    change_user_password,
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
from app.core.observability import client_ip, email_domain, log_event
from app.core.rate_limit import rate_limit
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(rate_limit("auth:register", limit=5, window_seconds=3600))],
)
def register(
    request: RegisterRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Register a new user. Sends verification email."""
    try:
        user = register_user(request, db, send_verification=False)
        background_tasks.add_task(send_verification_for_user, user.id)
        log_event(
            logger,
            logging.INFO,
            "auth.register.created",
            user_id=user.id,
            email_domain=email_domain(user.email),
            client_ip=client_ip(http_request),
        )
        return user
    except HTTPException as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth.register.failed",
            status_code=exc.status_code,
            email_domain=email_domain(request.email),
            client_ip=client_ip(http_request),
        )
        raise

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth:login", limit=10, window_seconds=300))],
)
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    """Login with email and password. Returns JWT tokens."""
    try:
        tokens = login_user(request, db)
        log_event(
            logger,
            logging.INFO,
            "auth.login.succeeded",
            email_domain=email_domain(request.email),
            client_ip=client_ip(http_request),
        )
        return tokens
    except HTTPException as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth.login.failed",
            status_code=exc.status_code,
            email_domain=email_domain(request.email),
            client_ip=client_ip(http_request),
        )
        raise

@router.post(
    "/token",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth:token", limit=10, window_seconds=300))],
)
def token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 login for the Swagger Authorize button. Use email as username."""
    try:
        tokens = login_user_by_email(form_data.username, form_data.password, db)
        log_event(
            logger,
            logging.INFO,
            "auth.token.succeeded",
            email_domain=email_domain(form_data.username),
            client_ip=client_ip(request),
        )
        return tokens
    except HTTPException as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth.token.failed",
            status_code=exc.status_code,
            email_domain=email_domain(form_data.username),
            client_ip=client_ip(request),
        )
        raise


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
def verify_email(token: str, request: Request, db: Session = Depends(get_db)):
    try:
        user = verify_user_email(token, db)
    except HTTPException as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth.email_verification.failed",
            status_code=exc.status_code,
            client_ip=client_ip(request),
        )
        raise
    log_event(
        logger,
        logging.INFO,
        "auth.email_verification.succeeded",
        user_id=user.id,
        client_ip=client_ip(request),
    )
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
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    if current_user.is_verified:
        log_event(
            logger,
            logging.INFO,
            "auth.verification_resend.skipped_verified",
            user_id=current_user.id,
            client_ip=client_ip(request),
        )
        return VerificationResponse(
            message="Email is already verified.",
            is_verified=True,
        )
    background_tasks.add_task(send_verification_for_user, current_user.id)
    log_event(
        logger,
        logging.INFO,
        "auth.verification_resend.queued",
        user_id=current_user.id,
        client_ip=client_ip(request),
    )
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
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_verification_recipient(request.email, db)
    if user:
        background_tasks.add_task(send_verification_for_user, user.id)
    log_event(
        logger,
        logging.INFO,
        "auth.public_verification_resend.requested",
        user_found=bool(user),
        email_domain=email_domain(request.email),
        client_ip=client_ip(http_request),
    )
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
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_password_reset_recipient(request.email, db)
    if user:
        background_tasks.add_task(send_password_reset_for_user, user.id)
    log_event(
        logger,
        logging.INFO,
        "auth.password_reset.requested",
        user_found=bool(user),
        email_domain=email_domain(request.email),
        client_ip=client_ip(http_request),
    )
    return {
        "message": "If this account exists, a password reset email has been sent."
    }


@router.post("/reset-password")
def reset_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    reset_user_password(request.token, request.password, db)
    return {"message": "Password reset successfully. You can now sign in."}


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        change_user_password(current_user, request, db)
    except HTTPException as exc:
        log_event(
            logger,
            logging.WARNING,
            "auth.password_change.failed",
            user_id=current_user.id,
            status_code=exc.status_code,
            client_ip=client_ip(http_request),
        )
        raise

    log_event(
        logger,
        logging.INFO,
        "auth.password_change.succeeded",
        user_id=current_user.id,
        client_ip=client_ip(http_request),
    )
    return {"message": "Password changed successfully. Please sign in again."}


@router.post("/test-email")
def test_email(to_email: str):
    """Send a test email to Mailtrap."""
    send_test_email(to_email)
    return {"message": "Test email sent"}

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenRefreshRequest,
    TokenResponse,
    VerificationResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    login_user,
    login_user_by_email,
    refresh_user_tokens,
    register_user,
    resend_user_verification,
    verify_user_email,
)
from app.services.email_service import send_test_email
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Sends verification email."""
    return register_user(request, db)

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password. Returns JWT tokens."""
    return login_user(request, db)

@router.post("/token", response_model=TokenResponse)
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


@router.post("/resend-verification", response_model=VerificationResponse)
def resend_verification(current_user: User = Depends(get_current_user)):
    queued = resend_user_verification(current_user)
    if not queued:
        return VerificationResponse(
            message="Email is already verified.",
            is_verified=True,
        )
    return VerificationResponse(
        message="Verification email sent.",
        is_verified=False,
    )


@router.post("/test-email")
def test_email(to_email: str):
    """Send a test email to Mailtrap."""
    send_test_email(to_email)
    return {"message": "Test email sent"}

import logging

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.tasks.email_tasks import send_verification_email

logger = logging.getLogger(__name__)


def _queue_verification_email(user_id: int) -> None:
    try:
        send_verification_email.delay(user_id)
    except Exception:
        logger.exception("Could not queue verification email for user %s", user_id)


def register_user(request: RegisterRequest, db: Session) -> User:
    # Check email not already registered
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check phone not already registered
    if db.query(User).filter(User.phone_number == request.phone_number).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    # Create user
    user = User(
        email=request.email,
        phone_number=request.phone_number,
        full_name=request.full_name,
        hashed_password=hash_password(request.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    _queue_verification_email(user.id)

    return user

def login_user(request: LoginRequest, db: Session) -> TokenResponse:
    return login_user_by_email(request.email, request.password, db)


def login_user_by_email(email: str, password: str, db: Session) -> TokenResponse:
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # TODO: Log this action to audit log
    # await audit_service.log("user_login", user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


def refresh_user_tokens(refresh_token: str, db: Session) -> TokenResponse:
    invalid_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise invalid_token
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise invalid_token from exc

    user = db.get(User, user_id)
    if not user:
        raise invalid_token
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return TokenResponse(
        access_token=create_access_token(data={"sub": str(user.id)}),
        refresh_token=create_refresh_token(data={"sub": str(user.id)}),
    )


def verify_user_email(token: str, db: Session) -> User:
    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification link.",
    )

    try:
        payload = decode_token(token)
        if payload.get("purpose") != "email_verification":
            raise invalid_token
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise invalid_token from exc

    user = db.get(User, user_id)
    if not user:
        raise invalid_token

    if not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)

    return user


def resend_user_verification(user: User) -> bool:
    if user.is_verified:
        return False
    try:
        send_verification_email.delay(user.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification email could not be queued. Try again shortly.",
        ) from exc
    return True

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return _create_token(
        data={**data, "type": "access"},
        expires_at=expires_at,
    )


def create_refresh_token(data: dict) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return _create_token(
        data={**data, "type": "refresh"},
        expires_at=expires_at,
    )


def create_email_verification_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS
    )
    return _create_token(
        data={"sub": str(user_id), "purpose": "email_verification"},
        expires_at=expires_at,
    )


def create_password_reset_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.PASSWORD_RESET_EXPIRE_HOURS
    )
    return _create_token(
        data={"sub": str(user_id), "purpose": "password_reset"},
        expires_at=expires_at,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def _create_token(data: dict, expires_at: datetime) -> str:
    payload = data.copy()
    payload.update({"exp": expires_at})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

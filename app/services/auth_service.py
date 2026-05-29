from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token

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

    # TODO Sprint 2: Send verification email via Celery task
    # send_verification_email.delay(user.id)

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

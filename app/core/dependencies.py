from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
        user_id = int(user_id)
    except (JWTError, ValueError) as exc:
        raise credentials_error from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_error

    return user


def require_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before continuing.",
        )
    return current_user


def require_admin(
    current_user: User = Depends(require_verified_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins only.",
        )
    return current_user


from datetime import datetime, timedelta, timezone
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import SubscriptionTier


GRACE_PERIOD_DAYS = 3


def require_active_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Blocks FREE users from premium routes. Use as a FastAPI dependency."""
    if current_user.subscription_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This content requires an active subscription. Visit /api/v1/payments/stk-push to subscribe.",
        )

    # Check subscription is active or inside the 3-day grace period.
    sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status.in_(
            [SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE_PERIOD]
        ),
    ).first()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription found.",
        )

    expires_at = sub.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    grace_ends_at = expires_at + timedelta(days=GRACE_PERIOD_DAYS)

    if sub.status == SubscriptionStatus.ACTIVE and expires_at < now <= grace_ends_at:
        return current_user

    if sub.status == SubscriptionStatus.ACTIVE and grace_ends_at < now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your subscription grace period has ended. Please renew to continue.",
        )

    if sub.status == SubscriptionStatus.GRACE_PERIOD:
        if grace_ends_at < now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your subscription grace period has ended. Please renew to continue.",
            )

    return current_user


def require_pro_subscription(
    current_user: User = Depends(require_active_subscription),
) -> User:
    """Blocks BASIC users from PRO-only routes."""
    if current_user.subscription_tier != SubscriptionTier.PRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This content requires a PRO subscription.",
        )
    return current_user

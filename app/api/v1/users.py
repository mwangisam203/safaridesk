from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, SubscriptionTier
from app.schemas.user import SubscriptionStatusResponse

router = APIRouter(prefix="/users", tags=["Users"])
GRACE_PERIOD_DAYS = 3


@router.get("/me/subscription", response_model=SubscriptionStatusResponse)
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    sub = db.query(Subscription).filter_by(user_id=current_user.id).first()

    if not sub:
        return SubscriptionStatusResponse(
            tier=SubscriptionTier.FREE,
            is_active=False,
            message="You are on the FREE tier. Subscribe to access all content.",
        )

    expires_at = sub.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    days_remaining = None
    if expires_at:
        delta = expires_at - now
        days_remaining = max(0, delta.days)

    if expires_at and expires_at < now:
        grace_ends_at = expires_at + timedelta(days=GRACE_PERIOD_DAYS)
        if sub.status == SubscriptionStatus.GRACE_PERIOD or now <= grace_ends_at:
            grace_delta = grace_ends_at - now
            grace_days_remaining = max(0, grace_delta.days)
            return SubscriptionStatusResponse(
                tier=current_user.subscription_tier,
                status=SubscriptionStatus.GRACE_PERIOD,
                started_at=sub.started_at,
                expires_at=expires_at,
                days_remaining=grace_days_remaining,
                is_active=True,
                message=f"Your {sub.tier.value.upper()} subscription is in grace period. Renew within {grace_days_remaining} day(s) to avoid downgrade.",
            )

        return SubscriptionStatusResponse(
            tier=current_user.subscription_tier,
            status=SubscriptionStatus.EXPIRED,
            started_at=sub.started_at,
            expires_at=expires_at,
            days_remaining=0,
            is_active=False,
            message=f"Your {sub.tier.value.upper()} subscription expired on {expires_at.strftime('%d %b %Y')}. Renew to continue.",
        )

    return SubscriptionStatusResponse(
        tier=current_user.subscription_tier,
        status=sub.status,
        started_at=sub.started_at,
        expires_at=expires_at,
        days_remaining=days_remaining,
        is_active=True,
        message=f"Your {sub.tier.value.upper()} subscription is active. {days_remaining} day(s) remaining.",
    )

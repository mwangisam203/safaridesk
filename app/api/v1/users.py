from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import User, SubscriptionTier
from app.schemas.user import AdminUserUpdate, SubscriptionStatusResponse, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])
GRACE_PERIOD_DAYS = 3
ADMIN_OVERRIDE_DAYS = 30


def _query_all(query):
    if hasattr(query, "all"):
        return query.all()
    row = query.first()
    return [row] if row else []


def _sync_admin_subscription_override(
    db: Session,
    user: User,
    tier: SubscriptionTier,
) -> None:
    now = datetime.now(timezone.utc)
    subscriptions = _query_all(db.query(Subscription).filter_by(user_id=user.id))

    if tier == SubscriptionTier.FREE:
        for sub in subscriptions:
            if sub.status in {
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.GRACE_PERIOD,
                SubscriptionStatus.PENDING,
            }:
                sub.status = SubscriptionStatus.EXPIRED
                sub.expires_at = now
        user.subscription_tier = SubscriptionTier.FREE
        return

    target_tier = SubscriptionTierInfo(tier.value)
    active_sub = next(
        (
            sub
            for sub in subscriptions
            if sub.status in {
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.GRACE_PERIOD,
                SubscriptionStatus.PENDING,
            }
        ),
        None,
    )

    for sub in subscriptions:
        if sub is not active_sub and sub.status in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.GRACE_PERIOD,
            SubscriptionStatus.PENDING,
        }:
            sub.status = SubscriptionStatus.EXPIRED

    if active_sub:
        active_sub.tier = target_tier
        active_sub.status = SubscriptionStatus.ACTIVE
        active_sub.started_at = now
        active_sub.expires_at = now + timedelta(days=ADMIN_OVERRIDE_DAYS)
    else:
        db.add(
            Subscription(
                user_id=user.id,
                tier=target_tier,
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                expires_at=now + timedelta(days=ADMIN_OVERRIDE_DAYS),
            )
        )

    user.subscription_tier = tier


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


@router.get("/admin/users", response_model=list[UserResponse])
def list_users_for_admin(
    q: str | None = Query(default=None, max_length=120),
    tier: SubscriptionTier | None = None,
    is_active: bool | None = None,
    is_verified: bool | None = None,
    is_admin: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(User)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
                User.phone_number.ilike(pattern),
            )
        )
    if tier is not None:
        query = query.filter(User.subscription_tier == tier)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    if is_admin is not None:
        query = query.filter(User.is_admin == is_admin)

    return query.order_by(User.created_at.desc(), User.id.desc()).all()


@router.patch("/admin/users/{user_id}", response_model=UserResponse)
def update_user_for_admin(
    user_id: int,
    request: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    updates = request.model_dump(exclude_unset=True)
    if (
        user.id == current_user.id
        and updates.get("is_admin") is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin access.",
        )

    subscription_tier = updates.pop("subscription_tier", None)

    for field, value in updates.items():
        setattr(user, field, value)

    if subscription_tier is not None:
        _sync_admin_subscription_override(db, user, subscription_tier)

    db.commit()
    db.refresh(user)
    return user

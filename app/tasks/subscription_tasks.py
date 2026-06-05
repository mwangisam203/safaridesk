import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import SubscriptionTier, User


logger = logging.getLogger(__name__)

GRACE_PERIOD_DAYS = 3


def _make_aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@celery_app.task(name="app.tasks.subscription_tasks.process_subscription_expirations")
def process_subscription_expirations():
    """
    Daily subscription lifecycle task.

    - ACTIVE subscriptions whose expires_at has passed enter GRACE_PERIOD.
    - GRACE_PERIOD subscriptions remain usable for 3 days after expires_at.
    - After grace ends, users are downgraded to FREE and subscriptions become EXPIRED.
    """
    db = SessionLocal()
    try:
        return process_expired_subscriptions(db)
    finally:
        db.close()


def process_expired_subscriptions(db, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    moved_to_grace = 0
    downgraded = 0

    candidates = db.query(Subscription).filter(
        Subscription.status.in_(
            [SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE_PERIOD]
        )
    ).all()

    for sub in candidates:
        expires_at = _make_aware(sub.expires_at)
        if not expires_at or expires_at >= now:
            continue

        if sub.status == SubscriptionStatus.ACTIVE:
            sub.status = SubscriptionStatus.GRACE_PERIOD
            moved_to_grace += 1
            continue

        grace_ends_at = expires_at + timedelta(days=GRACE_PERIOD_DAYS)
        if sub.status == SubscriptionStatus.GRACE_PERIOD and grace_ends_at < now:
            sub.status = SubscriptionStatus.EXPIRED
            user = db.get(User, sub.user_id)
            if user:
                user.subscription_tier = SubscriptionTier.FREE
            downgraded += 1

    if moved_to_grace or downgraded:
        db.commit()

    logger.info(
        "Subscription lifecycle processed: %s moved to grace, %s downgraded.",
        moved_to_grace,
        downgraded,
    )
    return {"moved_to_grace": moved_to_grace, "downgraded": downgraded}

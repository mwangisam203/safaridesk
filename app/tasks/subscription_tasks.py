import logging
from math import ceil
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.audit_log import AuditLog
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import SubscriptionTier, User
from app.tasks.email_tasks import send_subscription_renewal_reminder
from app.tasks.sms_tasks import send_subscription_renewal_reminder_sms


logger = logging.getLogger(__name__)

GRACE_PERIOD_DAYS = 3
REMINDER_DAYS = {1, 2, 3, 4}


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
    reminders_sent = 0

    candidates = db.query(Subscription).filter(
        Subscription.status.in_(
            [SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE_PERIOD]
        )
    ).all()

    for sub in candidates:
        expires_at = _make_aware(sub.expires_at)
        if not expires_at:
            continue

        if sub.status == SubscriptionStatus.ACTIVE and expires_at >= now:
            days_remaining = ceil((expires_at - now).total_seconds() / 86400)
            if days_remaining in REMINDER_DAYS and not _reminder_already_sent(db, sub, days_remaining):
                send_subscription_renewal_reminder.delay(sub.user_id, days_remaining)
                send_subscription_renewal_reminder_sms.delay(sub.user_id, days_remaining)
                _record_reminder_sent(db, sub, days_remaining)
                reminders_sent += 1
            continue

        if expires_at >= now:
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

    if moved_to_grace or downgraded or reminders_sent:
        db.commit()

    logger.info(
        "Subscription lifecycle processed: %s reminder(s), %s moved to grace, %s downgraded.",
        reminders_sent,
        moved_to_grace,
        downgraded,
    )
    return {
        "reminders_sent": reminders_sent,
        "moved_to_grace": moved_to_grace,
        "downgraded": downgraded,
    }


def _reminder_already_sent(db, sub: Subscription, days_remaining: int) -> bool:
    return db.query(AuditLog).filter_by(
        action="subscription_renewal_reminder_sent",
        entity_type="subscription",
        entity_id=str(sub.id),
        log_metadata={"days_remaining": days_remaining},
    ).first() is not None


def _record_reminder_sent(db, sub: Subscription, days_remaining: int) -> None:
    db.add(
        AuditLog(
            user_id=sub.user_id,
            action="subscription_renewal_reminder_sent",
            entity_type="subscription",
            entity_id=str(sub.id),
            log_metadata={"days_remaining": days_remaining},
        )
    )

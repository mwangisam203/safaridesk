from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models.notification import Notification
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User


EXPIRY_NOTICE_DAYS = 4


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_notification(
    db,
    *,
    user_id: int,
    title: str,
    body: str,
    category: str = "account",
    action_url: str | None = None,
    event_key: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        body=body,
        category=category,
        action_url=action_url,
        event_key=event_key,
    )
    db.add(notification)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Notification)
            .filter_by(user_id=user_id, event_key=event_key)
            .first()
        )
        if existing:
            return existing
        raise
    return notification


def create_notification_once(
    db,
    *,
    user_id: int,
    event_key: str,
    title: str,
    body: str,
    category: str = "account",
    action_url: str | None = None,
) -> Notification:
    existing = (
        db.query(Notification)
        .filter_by(user_id=user_id, event_key=event_key)
        .first()
    )
    if existing:
        return existing

    return create_notification(
        db,
        user_id=user_id,
        event_key=event_key,
        title=title,
        body=body,
        category=category,
        action_url=action_url,
    )


def notify_payment_completed(db, *, user_id: int, transaction_id: int, tier: str, amount: str) -> None:
    create_notification_once(
        db,
        user_id=user_id,
        event_key=f"payment:{transaction_id}:completed",
        category="payment",
        title="Payment confirmed",
        body=f"Your KES {amount} payment was confirmed. {tier.upper()} access is now updated.",
        action_url="/account",
    )


def notify_payment_failed(
    db,
    *,
    user_id: int,
    transaction_id: int,
    reason: str,
    cancelled: bool = False,
) -> None:
    create_notification_once(
        db,
        user_id=user_id,
        event_key=f"payment:{transaction_id}:{'cancelled' if cancelled else 'failed'}",
        category="payment",
        title="Payment cancelled" if cancelled else "Payment failed",
        body=reason or "Your M-Pesa payment was not completed.",
        action_url="/plans",
    )


def ensure_account_notifications(db, user: User) -> None:
    if not user.is_verified:
        create_notification_once(
            db,
            user_id=user.id,
            event_key="account:email-verification",
            category="account",
            title="Verify your email",
            body="Verify your email before starting payments or using admin actions.",
            action_url="/account",
        )

    now = datetime.now(timezone.utc)
    subscriptions = (
        db.query(Subscription)
        .filter_by(user_id=user.id)
        .all()
    )

    for sub in subscriptions:
        expires_at = _aware_utc(sub.expires_at)
        if not expires_at:
            continue

        days_remaining = max(0, (expires_at - now).days)

        if sub.status == SubscriptionStatus.ACTIVE and now <= expires_at:
            if days_remaining <= EXPIRY_NOTICE_DAYS:
                create_notification_once(
                    db,
                    user_id=user.id,
                    event_key=f"subscription:{sub.id}:expires:{days_remaining}",
                    category="subscription",
                    title=f"{sub.tier.value.upper()} expires soon",
                    body=f"Your subscription has {days_remaining} day(s) remaining.",
                    action_url="/plans",
                )
        elif sub.status == SubscriptionStatus.GRACE_PERIOD:
            create_notification_once(
                db,
                user_id=user.id,
                event_key=f"subscription:{sub.id}:grace",
                category="subscription",
                title="Subscription grace period",
                body="Your subscription is in grace period. Renew to avoid returning to FREE access.",
                action_url="/plans",
            )
        elif sub.status == SubscriptionStatus.EXPIRED:
            create_notification_once(
                db,
                user_id=user.id,
                event_key=f"subscription:{sub.id}:expired",
                category="subscription",
                title="Subscription expired",
                body="Your paid access has ended. Choose a plan to continue reading subscriber content.",
                action_url="/plans",
            )


def list_user_notifications(db, user: User, limit: int = 20) -> tuple[list[Notification], int]:
    ensure_account_notifications(db, user)
    notifications = (
        db.query(Notification)
        .filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )
    unread_count = (
        db.query(Notification)
        .filter_by(user_id=user.id, read_at=None)
        .count()
    )
    return notifications, unread_count


def mark_notification_read(db, *, user_id: int, notification_id: int) -> Notification | None:
    notification = (
        db.query(Notification)
        .filter_by(id=notification_id, user_id=user_id)
        .first()
    )
    if not notification:
        return None
    if not notification.read_at:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
    return notification


def mark_all_notifications_read(db, *, user_id: int) -> int:
    notifications = (
        db.query(Notification)
        .filter_by(user_id=user_id, read_at=None)
        .all()
    )
    now = datetime.now(timezone.utc)
    for notification in notifications:
        notification.read_at = now
    if notifications:
        db.commit()
    return len(notifications)

import logging
from decimal import Decimal

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.subscription import Subscription
from app.models.user import User
from app.services.sms_service import send_sms

logger = logging.getLogger(__name__)


def _format_money(amount: Decimal | float | int | str, currency: str = "KES") -> str:
    value = Decimal(str(amount))
    return f"{currency} {value:,.2f}"


@celery_app.task(name="app.tasks.sms_tasks.send_payment_confirmation_sms")
def send_payment_confirmation_sms(user_id: int, amount: str | float | int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            logger.warning(
                "Payment confirmation SMS skipped: user %s not found", user_id
            )
            return

        subscription = (
            db.query(Subscription)
            .filter_by(user_id=user_id)
            .order_by(Subscription.expires_at.desc())
            .first()
        )

        tier = subscription.tier.value if subscription else user.subscription_tier.value
        expires_at = subscription.expires_at if subscription else None
        expiry_text = f" until {expires_at:%b} {expires_at.day}" if expires_at else ""

        send_sms(
            to_phone=user.phone_number,
            message=(
                f"SafariDesk: Payment of {_format_money(amount)} confirmed. "
                f"Your {tier.upper()} subscription is active{expiry_text}. Enjoy!"
            ),
        )
    except Exception:
        logger.exception("Payment confirmation SMS failed for user %s", user_id)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.sms_tasks.send_subscription_renewal_reminder_sms")
def send_subscription_renewal_reminder_sms(user_id: int, days_remaining: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            logger.warning("Renewal reminder SMS skipped: user %s not found", user_id)
            return

        subscription = (
            db.query(Subscription)
            .filter_by(user_id=user_id)
            .order_by(Subscription.expires_at.desc())
            .first()
        )
        if not subscription:
            logger.warning(
                "Renewal reminder SMS skipped: subscription for user %s not found",
                user_id,
            )
            return

        send_sms(
            to_phone=user.phone_number,
            message=(
                f"SafariDesk: Your {subscription.tier.value.upper()} subscription expires "
                f"in {days_remaining} day(s) on {subscription.expires_at:%b} {subscription.expires_at.day}. "
                "Renew to keep paid access."
            ),
        )
    except Exception:
        logger.exception("Renewal reminder SMS failed for user %s", user_id)
        raise
    finally:
        db.close()

import logging
from decimal import Decimal

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.subscription import Subscription
from app.models.user import User
from app.core.config import settings
from app.core.security import create_email_verification_token
from app.core.security import create_password_reset_token
from app.services.email_service import send_email

logger = logging.getLogger(__name__)


def _format_money(amount: Decimal | float | int | str, currency: str = "KES") -> str:
    value = Decimal(str(amount))
    return f"{currency} {value:,.2f}"


def send_verification_email_now(user_id: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user or user.is_verified:
            return

        token = create_email_verification_token(user.id)
        verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={token}"
        send_email(
            to_email=user.email,
            subject="Verify your SafariDesk email",
            body=(
                f"Hi {user.full_name},\n\n"
                "Verify your SafariDesk email by opening this link:\n"
                f"{verification_url}\n\n"
                f"This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours.\n\n"
                "If you did not create this account, you can ignore this email.\n\n"
                "SafariDesk"
            ),
        )
    except Exception:
        logger.exception("Verification email failed for user %s", user_id)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.send_verification_email")
def send_verification_email(user_id: int) -> None:
    send_verification_email_now(user_id)


def send_password_reset_email_now(user_id: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user or not user.is_active:
            return

        token = create_password_reset_token(user.id)
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
        send_email(
            to_email=user.email,
            subject="Reset your SafariDesk password",
            body=(
                f"Hi {user.full_name},\n\n"
                "Reset your SafariDesk password by opening this link:\n"
                f"{reset_url}\n\n"
                f"This link expires in {settings.PASSWORD_RESET_EXPIRE_HOURS} hour(s).\n\n"
                "If you did not request this reset, you can ignore this email.\n\n"
                "SafariDesk"
            ),
        )
    except Exception:
        logger.exception("Password reset email failed for user %s", user_id)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.send_password_reset_email")
def send_password_reset_email(user_id: int) -> None:
    send_password_reset_email_now(user_id)


@celery_app.task(name="app.tasks.email_tasks.send_payment_confirmation")
def send_payment_confirmation(
    user_id: int, receipt_number: str | None, amount: str | float | int
) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            logger.warning(
                "Payment confirmation email skipped: user %s not found", user_id
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
        expiry_line = (
            f"\nYour subscription is active until {expires_at:%d %b %Y}."
            if expires_at
            else ""
        )
        receipt_line = f"\nM-Pesa receipt: {receipt_number}" if receipt_number else ""

        send_email(
            to_email=user.email,
            subject="SafariDesk payment confirmed",
            body=(
                f"Hi {user.full_name},\n\n"
                f"We have received your payment of {_format_money(amount)} for the {tier.upper()} plan."
                f"{receipt_line}"
                f"{expiry_line}\n\n"
                "Your SafariDesk subscription is ready to use.\n\n"
                "Thank you,\n"
                "SafariDesk"
            ),
        )
    except Exception:
        logger.exception("Payment confirmation email failed for user %s", user_id)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.send_payment_failed")
def send_payment_failed(
    user_id: int, amount: str | float | int, reason: str | None = None
) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            logger.warning("Payment failure email skipped: user %s not found", user_id)
            return

        reason_line = f"\nReason: {reason}" if reason else ""
        send_email(
            to_email=user.email,
            subject="SafariDesk payment was not completed",
            body=(
                f"Hi {user.full_name},\n\n"
                f"Your payment of {_format_money(amount)} was not completed."
                f"{reason_line}\n\n"
                "You can try again from your SafariDesk account.\n\n"
                "Thank you,\n"
                "SafariDesk"
            ),
        )
    except Exception:
        logger.exception("Payment failure email failed for user %s", user_id)
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.email_tasks.send_subscription_renewal_reminder")
def send_subscription_renewal_reminder(user_id: int, days_remaining: int) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            logger.warning("Renewal reminder email skipped: user %s not found", user_id)
            return

        subscription = (
            db.query(Subscription)
            .filter_by(user_id=user_id)
            .order_by(Subscription.expires_at.desc())
            .first()
        )
        if not subscription:
            logger.warning(
                "Renewal reminder email skipped: subscription for user %s not found",
                user_id,
            )
            return

        send_email(
            to_email=user.email,
            subject="SafariDesk subscription renewal reminder",
            body=(
                f"Hi {user.full_name},\n\n"
                f"Your {subscription.tier.value.upper()} subscription expires in {days_remaining} day(s), "
                f"on {subscription.expires_at:%d %b %Y}.\n\n"
                "Renew before it expires to avoid entering grace period and losing paid access.\n\n"
                "Thank you,\n"
                "SafariDesk"
            ),
        )
    except Exception:
        logger.exception("Renewal reminder email failed for user %s", user_id)
        raise
    finally:
        db.close()

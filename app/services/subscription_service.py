from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING

from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import User, SubscriptionTier

TIER_DURATIONS = {"free": 0, "basic": 30, "pro": 30}  # days
TIER_PRICES = {"basic": Decimal("1"), "pro": Decimal("5")}  # KES
TIER_RANK = {"free": 0, "basic": 1, "pro": 2}


def _make_aware(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware (UTC).
    SQLAlchemy can return naive datetimes even from timezone columns
    depending on the driver — this guards against that.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _mpesa_amount(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_CEILING))


class SubscriptionService:
    def __init__(self, db):
        self.db = db

    def quote(self, user_id: int, tier: str) -> dict:
        tier_info = SubscriptionTierInfo(tier)
        now = datetime.now(timezone.utc)
        target_price = TIER_PRICES[tier_info.value]
        duration = TIER_DURATIONS.get(tier_info.value, 30)

        quote = {
            "tier": tier_info.value,
            "amount": _mpesa_amount(target_price),
            "original_amount": _money(target_price),
            "credit_applied": Decimal("0.00"),
            "duration_days": duration,
            "mode": "new",
        }

        sub = self.db.query(Subscription).filter_by(user_id=user_id).first()
        if not sub:
            return quote

        expires_at = _make_aware(sub.expires_at)
        if not expires_at or expires_at <= now:
            quote["mode"] = "renew"
            return quote

        current_tier = sub.tier.value
        if current_tier == tier_info.value:
            quote["mode"] = "renew"
            return quote

        if TIER_RANK.get(current_tier, 0) < TIER_RANK.get(tier_info.value, 0):
            current_price = TIER_PRICES.get(current_tier, Decimal("0"))
            current_duration = TIER_DURATIONS.get(current_tier, 30)
            remaining_seconds = Decimal(str((expires_at - now).total_seconds()))
            duration_seconds = Decimal(current_duration * 24 * 60 * 60)
            unused_ratio = max(Decimal("0"), min(Decimal("1"), remaining_seconds / duration_seconds))
            credit = _money(current_price * unused_ratio)
            amount_due = max(Decimal("0"), target_price - credit)

            quote.update(
                {
                    "amount": _mpesa_amount(amount_due),
                    "credit_applied": credit,
                    "mode": "upgrade",
                }
            )
            return quote

        quote["mode"] = "change"
        return quote

    def activate(
        self,
        user_id: int,
        tier: str,
        amount_paid: Decimal | int | float | str | None = None,
    ) -> Subscription:
        """
        Activate or extend a subscription after a successful M-Pesa payment.

        - If the user already has a subscription, extend it from the current
          expiry date (or from now if already expired).
        - If no subscription exists, create a fresh one.
        - Always syncs the denormalized `subscription_tier` on the User row
          for fast reads without a join.

        Args:
            user_id: ID of the user being activated.
            tier:    Tier string — "basic" or "pro" (from txn.tier.value).

        Returns:
            The updated or newly created Subscription instance.
        """
        # Convert string → correct enums for both models
        # e.g. "basic" → SubscriptionTierInfo.BASIC, SubscriptionTier.BASIC
        tier_info = SubscriptionTierInfo(tier)       # for Subscription.tier
        tier_user = SubscriptionTier(tier)           # for User.subscription_tier

        now = datetime.now(timezone.utc)
        duration = TIER_DURATIONS.get(tier, 30)

        sub = self.db.query(Subscription).filter_by(user_id=user_id).first()

        if sub:
            # Make expires_at timezone-aware before comparison
            # (guards against naive datetimes from the DB driver)
            expires_aware = _make_aware(sub.expires_at)

            is_same_tier = sub.tier == tier_info
            is_active = expires_aware and expires_aware > now

            # Same-tier renewals extend from current expiry. Tier changes start
            # a fresh target-tier term from now so lower-tier days do not become
            # full higher-tier days.
            base = expires_aware if (is_same_tier and is_active) else now

            sub.tier       = tier_info
            sub.status     = SubscriptionStatus.ACTIVE
            sub.started_at = now if not is_same_tier else sub.started_at
            sub.expires_at = base + timedelta(days=duration)
            if amount_paid is not None:
                sub.amount_paid = Decimal(str(amount_paid))

        else:
            sub = Subscription(
                user_id=user_id,
                tier=tier_info,
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                expires_at=now + timedelta(days=duration),
                amount_paid=Decimal(str(amount_paid)) if amount_paid is not None else None,
            )
            self.db.add(sub)

        # Sync denormalized tier on User — SQLAlchemy 2.0 style
        user = self.db.get(User, user_id)
        if user:
            user.subscription_tier = tier_user

        self.db.commit()
        return sub

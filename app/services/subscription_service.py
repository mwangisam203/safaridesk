from datetime import datetime, timedelta, timezone

from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import User, SubscriptionTier

TIER_DURATIONS = {"free": 0, "basic": 30, "pro": 30}  # days


def _make_aware(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware (UTC).
    SQLAlchemy can return naive datetimes even from timezone columns
    depending on the driver — this guards against that.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SubscriptionService:
    def __init__(self, db):
        self.db = db

    def activate(self, user_id: int, tier: str) -> Subscription:
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

            # Extend from current expiry if still active, otherwise from now
            base = expires_aware if (expires_aware and expires_aware > now) else now

            sub.tier       = tier_info
            sub.status     = SubscriptionStatus.ACTIVE
            sub.expires_at = base + timedelta(days=duration)

        else:
            sub = Subscription(
                user_id=user_id,
                tier=tier_info,
                status=SubscriptionStatus.ACTIVE,
                started_at=now,
                expires_at=now + timedelta(days=duration),
            )
            self.db.add(sub)

        # Sync denormalized tier on User — SQLAlchemy 2.0 style
        user = self.db.get(User, user_id)
        if user:
            user.subscription_tier = tier_user

        self.db.commit()
        return sub
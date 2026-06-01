from datetime import datetime, timedelta, timezone
from app.models.subscription import Subscription
from app.models.user import User

TIER_DURATIONS = {"basic": 30, "pro": 30}  # days

class SubscriptionService:
    def __init__(self, db):
        self.db = db

    def activate(self, user_id: int, tier: str):
        now = datetime.now(timezone.utc)
        sub = self.db.query(Subscription).filter_by(user_id=user_id).first()

        if sub:
            # Extend if already active, otherwise reset from now
            base = sub.expires_at if sub.expires_at > now else now
            sub.expires_at = base + timedelta(days=TIER_DURATIONS[tier])
            sub.tier   = tier
            sub.status = "active"
        else:
            sub = Subscription(
                user_id=user_id,
                tier=tier,
                status="active",
                started_at=now,
                expires_at=now + timedelta(days=TIER_DURATIONS[tier]),
            )
            self.db.add(sub)

        # Also update denormalized tier on User for fast reads
        user = self.db.query(User).get(user_id)
        user.subscription_tier = tier
        self.db.commit()
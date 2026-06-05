from datetime import datetime, timezone

from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import SubscriptionTier, User
from app.tasks import sms_tasks


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.criteria = {}

    def get(self, row_id):
        return next((row for row in self.rows if row.id == row_id), None)

    def filter_by(self, **criteria):
        self.criteria = criteria
        return self

    def order_by(self, *args):
        return self

    def first(self):
        for row in self.rows:
            if all(getattr(row, key) == value for key, value in self.criteria.items()):
                return row
        return None


class FakeDb:
    def __init__(self, users=None, subscriptions=None):
        self.users = users or []
        self.subscriptions = subscriptions or []
        self.closed = False

    def query(self, model):
        rows = {
            User: self.users,
            Subscription: self.subscriptions,
        }.get(model, [])
        return FakeQuery(rows)

    def close(self):
        self.closed = True


def test_payment_confirmation_sms_uses_user_phone_and_subscription_expiry(monkeypatch):
    user = User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=SubscriptionTier.BASIC,
    )
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        expires_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])
    sent = {}

    monkeypatch.setattr(sms_tasks, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(sms_tasks, "send_sms", lambda **kwargs: sent.update(kwargs))

    sms_tasks.send_payment_confirmation_sms(user.id, "500")

    assert sent == {
        "to_phone": "+254700000001",
        "message": (
            "SafariDesk: Payment of KES 500.00 confirmed. "
            "Your BASIC subscription is active until Jul 2. Enjoy!"
        ),
    }
    assert fake_db.closed is True


def test_renewal_reminder_sms_uses_user_phone_and_days_remaining(monkeypatch):
    user = User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=SubscriptionTier.BASIC,
    )
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        expires_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])
    sent = {}

    monkeypatch.setattr(sms_tasks, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(sms_tasks, "send_sms", lambda **kwargs: sent.update(kwargs))

    sms_tasks.send_subscription_renewal_reminder_sms(user.id, 4)

    assert sent == {
        "to_phone": "+254700000001",
        "message": (
            "SafariDesk: Your BASIC subscription expires in 4 day(s) on Jul 2. "
            "Renew to keep paid access."
        ),
    }
    assert fake_db.closed is True

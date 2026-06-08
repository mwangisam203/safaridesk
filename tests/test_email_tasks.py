from datetime import datetime, timezone

from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import SubscriptionTier, User
from app.tasks import email_tasks


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


def test_verification_email_contains_signed_link(monkeypatch):
    user = User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=SubscriptionTier.FREE,
        is_verified=False,
    )
    fake_db = FakeDb(users=[user])
    sent = {}

    monkeypatch.setattr(email_tasks, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(email_tasks, "send_email", lambda **kwargs: sent.update(kwargs))
    monkeypatch.setattr(email_tasks.settings, "APP_BASE_URL", "http://localhost:8000")

    email_tasks.send_verification_email(user.id)

    assert sent["to_email"] == "sam@example.com"
    assert sent["subject"] == "Verify your SafariDesk email"
    assert "http://localhost:8000/api/v1/auth/verify-email?token=" in sent["body"]
    assert "expires in 24 hours" in sent["body"]
    assert fake_db.closed is True


def test_renewal_reminder_email_uses_subscription_expiry(monkeypatch):
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

    monkeypatch.setattr(email_tasks, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(email_tasks, "send_email", lambda **kwargs: sent.update(kwargs))

    email_tasks.send_subscription_renewal_reminder(user.id, 4)

    assert sent["to_email"] == "sam@example.com"
    assert sent["subject"] == "SafariDesk subscription renewal reminder"
    assert "Hi Samson" in sent["body"]
    assert "BASIC subscription expires in 4 day(s)" in sent["body"]
    assert "02 Jul 2026" in sent["body"]
    assert fake_db.closed is True

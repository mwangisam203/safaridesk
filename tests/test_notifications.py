from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core import dependencies
from app.db import session
from app.models.notification import Notification
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import SubscriptionTier, User
from main import app


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.criteria = {}
        self.limit_value = None

    def filter_by(self, **criteria):
        self.criteria.update(criteria)
        return self

    def order_by(self, *args):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        rows = [
            row for row in self.rows
            if all(getattr(row, key) == value for key, value in self.criteria.items())
        ]
        rows = sorted(rows, key=lambda row: (row.created_at or datetime.min.replace(tzinfo=timezone.utc), row.id or 0), reverse=True)
        return rows[: self.limit_value] if self.limit_value else rows

    def first(self):
        rows = self.all()
        return rows[0] if rows else None

    def count(self):
        return len(self.all())


class FakeDb:
    def __init__(self, notifications=None, subscriptions=None):
        self.notifications = notifications or []
        self.subscriptions = subscriptions or []
        self.commits = 0

    def add(self, row):
        if isinstance(row, Notification):
            row.id = row.id or len(self.notifications) + 1
            row.created_at = row.created_at or datetime.now(timezone.utc)
            self.notifications.append(row)
        if isinstance(row, Subscription):
            self.subscriptions.append(row)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def query(self, model):
        if model is Notification:
            return FakeQuery(self.notifications)
        if model is Subscription:
            return FakeQuery(self.subscriptions)
        return FakeQuery([])


def make_user(is_verified=False):
    return User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=SubscriptionTier.BASIC,
        is_active=True,
        is_verified=is_verified,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
    )


def make_client(fake_db, user):
    app.dependency_overrides[session.get_db] = lambda: fake_db
    app.dependency_overrides[dependencies.get_current_user] = lambda: user
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_notifications_include_account_and_subscription_notices():
    user = make_user(is_verified=False)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=datetime.now(timezone.utc) - timedelta(days=27),
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
    )
    fake_db = FakeDb(subscriptions=[subscription])

    response = make_client(fake_db, user).get("/api/v1/notifications")

    assert response.status_code == 200
    payload = response.json()
    assert payload["unread_count"] == 2
    titles = {item["title"] for item in payload["notifications"]}
    assert "Verify your email" in titles
    assert "BASIC expires soon" in titles


def test_mark_notification_read_only_updates_current_user_notification():
    user = make_user(is_verified=True)
    notification = Notification(
        id=9,
        user_id=user.id,
        category="payment",
        title="Payment confirmed",
        body="Your payment was confirmed.",
        created_at=datetime.now(timezone.utc),
    )
    other_notification = Notification(
        id=10,
        user_id=99,
        category="payment",
        title="Other",
        body="Not yours.",
        created_at=datetime.now(timezone.utc),
    )
    fake_db = FakeDb(notifications=[notification, other_notification])

    response = make_client(fake_db, user).patch("/api/v1/notifications/9/read")

    assert response.status_code == 200
    assert response.json()["read_at"] is not None
    assert notification.read_at is not None
    assert other_notification.read_at is None

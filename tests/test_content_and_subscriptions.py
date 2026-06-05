from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.v1 import content
from app.core import dependencies
from app.db import session
from app.models.article import Article, ArticleTier
from app.models.free_article_read import FreeArticleRead
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import SubscriptionTier, User
from app.services.subscription_service import SubscriptionService
from app.tasks.subscription_tasks import process_expired_subscriptions
from main import app


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.criteria = {}

    def filter_by(self, **criteria):
        self.criteria = criteria
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        for row in self.rows:
            if all(getattr(row, key) == value for key, value in self.criteria.items()):
                return row
        return None

    def count(self):
        return len(self.rows)

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, articles=None, users=None, subscriptions=None, free_reads=None):
        self.articles = articles or []
        self.users = users or []
        self.subscriptions = subscriptions or []
        self.free_reads = free_reads or []
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, row):
        self.added.append(row)
        if isinstance(row, Article):
            self.articles.append(row)
        if isinstance(row, FreeArticleRead):
            self.free_reads.append(row)
        if isinstance(row, Subscription):
            self.subscriptions.append(row)

    def commit(self):
        self.commits += 1

    def refresh(self, row):
        self.refreshed.append(row)
        if getattr(row, "id", None) is None:
            row.id = len(self.added)
        if isinstance(row, Article):
            if row.created_at is None:
                row.created_at = datetime.now(timezone.utc)
            if row.view_count is None:
                row.view_count = 0

    def delete(self, row):
        if isinstance(row, Article):
            self.articles.remove(row)

    def get(self, model, row_id):
        rows = {
            User: self.users,
            Article: self.articles,
            Subscription: self.subscriptions,
        }.get(model, [])
        return next((row for row in rows if row.id == row_id), None)

    def query(self, model):
        rows = {
            Article: self.articles,
            User: self.users,
            Subscription: self.subscriptions,
            FreeArticleRead: self.free_reads,
        }.get(model, [])
        return FakeQuery(rows)


def make_article(tier=ArticleTier.BASIC, slug="fastapi-payments", is_published=True):
    now = datetime.now(timezone.utc)
    return Article(
        id=10,
        title="Understanding FastAPI Payments",
        slug=slug,
        summary="A practical payment flow overview.",
        body="This article explains the full subscription payment workflow.",
        tier=tier,
        author="SafariDesk Team",
        is_published=is_published,
        view_count=0,
        created_at=now,
        published_at=now if is_published else None,
    )


def make_user(tier=SubscriptionTier.FREE, is_admin=False):
    return User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=tier,
        is_active=True,
        is_verified=False,
        is_admin=is_admin,
        created_at=datetime.now(timezone.utc),
    )


def make_client(fake_db):
    app.dependency_overrides[session.get_db] = lambda: fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_anonymous_user_cannot_read_pro_article():
    article = make_article(tier=ArticleTier.PRO)
    fake_db = FakeDb(articles=[article])

    response = make_client(fake_db).get("/api/v1/content/articles/fastapi-payments")

    assert response.status_code == 403
    assert response.json()["detail"]["action"] == "register"
    assert article.view_count == 0
    assert fake_db.added == []
    assert fake_db.commits == 0


def test_free_user_at_read_limit_is_prompted_to_subscribe(monkeypatch):
    article = make_article()
    user = make_user(tier=SubscriptionTier.FREE)
    fake_db = FakeDb(articles=[article], users=[user])

    monkeypatch.setattr("app.core.security.decode_token", lambda token: {"sub": str(user.id)})
    monkeypatch.setattr(content, "already_read", lambda user_id, article_id, db: False)
    monkeypatch.setattr(content, "get_free_reads_count", lambda user_id, db: content.FREE_ARTICLE_LIMIT)

    response = make_client(fake_db).get(
        "/api/v1/content/articles/fastapi-payments",
        headers={"Authorization": "Bearer valid-token"},
    )

    detail = response.json()["detail"]
    assert response.status_code == 403
    assert detail["action"] == "subscribe"
    assert detail["subscribe_url"] == "/api/v1/payments/stk-push"
    assert article.view_count == 0
    assert fake_db.added == []


def test_basic_subscriber_can_read_basic_article_without_free_read_tracking(monkeypatch):
    article = make_article()
    user = make_user(tier=SubscriptionTier.BASIC)
    fake_db = FakeDb(articles=[article], users=[user])

    monkeypatch.setattr("app.core.security.decode_token", lambda token: {"sub": str(user.id)})

    response = make_client(fake_db).get(
        "/api/v1/content/articles/fastapi-payments",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "fastapi-payments"
    assert article.view_count == 1
    assert fake_db.added == []
    assert fake_db.commits == 1


def test_expired_subscription_status_returns_inactive():
    now = datetime.now(timezone.utc)
    user = make_user(tier=SubscriptionTier.BASIC)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=now - timedelta(days=40),
        expires_at=now - timedelta(days=10),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])

    app.dependency_overrides[dependencies.get_current_user] = lambda: user
    response = make_client(fake_db).get("/api/v1/users/me/subscription")

    body = response.json()
    assert response.status_code == 200
    assert body["tier"] == "basic"
    assert body["is_active"] is False
    assert body["days_remaining"] == 0
    assert "expired" in body["message"]


def test_subscription_status_reports_grace_period_as_active():
    now = datetime.now(timezone.utc)
    user = make_user(tier=SubscriptionTier.BASIC)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.GRACE_PERIOD,
        started_at=now - timedelta(days=35),
        expires_at=now - timedelta(days=1),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])

    app.dependency_overrides[dependencies.get_current_user] = lambda: user
    response = make_client(fake_db).get("/api/v1/users/me/subscription")

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "grace_period"
    assert body["is_active"] is True
    assert body["days_remaining"] >= 1
    assert "grace period" in body["message"]


def test_subscription_activation_creates_subscription_and_syncs_user_tier():
    user = make_user()
    fake_db = FakeDb(users=[user])

    subscription = SubscriptionService(fake_db).activate(user.id, "basic")

    assert subscription in fake_db.subscriptions
    assert subscription.user_id == user.id
    assert subscription.tier == SubscriptionTierInfo.BASIC
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.expires_at > datetime.now(timezone.utc)
    assert user.subscription_tier == SubscriptionTier.BASIC
    assert fake_db.commits == 1


def test_subscription_activation_extends_active_subscription_from_current_expiry():
    now = datetime.now(timezone.utc)
    user = make_user(tier=SubscriptionTier.BASIC)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=now - timedelta(days=10),
        expires_at=now + timedelta(days=15),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])

    updated = SubscriptionService(fake_db).activate(user.id, "basic")

    expected_expiry = subscription.expires_at
    assert updated is subscription
    assert 44 <= (expected_expiry - now).days <= 45
    assert user.subscription_tier == SubscriptionTier.BASIC
    assert fake_db.commits == 1


def test_subscription_activation_renews_expired_subscription_from_now():
    now = datetime.now(timezone.utc)
    user = make_user(tier=SubscriptionTier.BASIC)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=now - timedelta(days=60),
        expires_at=now - timedelta(days=5),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])

    updated = SubscriptionService(fake_db).activate(user.id, "pro")

    assert updated is subscription
    assert updated.tier == SubscriptionTierInfo.PRO
    assert 29 <= (updated.expires_at - now).days <= 30
    assert user.subscription_tier == SubscriptionTier.PRO
    assert fake_db.commits == 1


def test_expiration_task_moves_expired_active_subscription_to_grace_period():
    now = datetime.now(timezone.utc)
    user = make_user(tier=SubscriptionTier.BASIC)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.BASIC,
        status=SubscriptionStatus.ACTIVE,
        started_at=now - timedelta(days=31),
        expires_at=now - timedelta(days=1),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])

    result = process_expired_subscriptions(fake_db, now=now)

    assert result == {"moved_to_grace": 1, "downgraded": 0}
    assert subscription.status == SubscriptionStatus.GRACE_PERIOD
    assert user.subscription_tier == SubscriptionTier.BASIC
    assert fake_db.commits == 1


def test_expiration_task_downgrades_user_after_grace_period_ends():
    now = datetime.now(timezone.utc)
    user = make_user(tier=SubscriptionTier.PRO)
    subscription = Subscription(
        id=3,
        user_id=user.id,
        tier=SubscriptionTierInfo.PRO,
        status=SubscriptionStatus.GRACE_PERIOD,
        started_at=now - timedelta(days=40),
        expires_at=now - timedelta(days=4),
    )
    fake_db = FakeDb(users=[user], subscriptions=[subscription])

    result = process_expired_subscriptions(fake_db, now=now)

    assert result == {"moved_to_grace": 0, "downgraded": 1}
    assert subscription.status == SubscriptionStatus.EXPIRED
    assert user.subscription_tier == SubscriptionTier.FREE
    assert fake_db.commits == 1


def test_non_admin_cannot_create_article():
    user = make_user(is_admin=False)
    fake_db = FakeDb(users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post(
        "/api/v1/content/admin/articles",
        json={
            "title": "Building Payment APIs",
            "slug": "building-payment-apis",
            "summary": "Payment API notes.",
            "body": "A detailed guide to building payment APIs.",
            "tier": "basic",
            "is_published": True,
        },
    )

    assert response.status_code == 403
    assert fake_db.added == []
    assert fake_db.commits == 0


def test_admin_can_create_published_article():
    user = make_user(is_admin=True)
    fake_db = FakeDb(users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post(
        "/api/v1/content/admin/articles",
        json={
            "title": "Building Payment APIs",
            "slug": "building-payment-apis",
            "summary": "Payment API notes.",
            "body": "A detailed guide to building payment APIs.",
            "tier": "basic",
            "is_published": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "building-payment-apis"
    assert fake_db.articles[0].published_at is not None
    assert fake_db.commits == 1


def test_admin_create_article_rejects_duplicate_slug():
    user = make_user(is_admin=True)
    existing = make_article(slug="building-payment-apis")
    fake_db = FakeDb(articles=[existing], users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post(
        "/api/v1/content/admin/articles",
        json={
            "title": "Building Payment APIs",
            "slug": "building-payment-apis",
            "summary": "Payment API notes.",
            "body": "A detailed guide to building payment APIs.",
            "tier": "basic",
            "is_published": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Slug already exists."
    assert fake_db.commits == 0


def test_admin_can_update_article_and_set_published_at():
    user = make_user(is_admin=True)
    article = make_article(is_published=False)
    fake_db = FakeDb(articles=[article], users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).patch(
        "/api/v1/content/admin/articles/fastapi-payments",
        json={"title": "Updated Payment APIs", "is_published": True},
    )

    assert response.status_code == 200
    assert article.title == "Updated Payment APIs"
    assert article.published_at is not None
    assert fake_db.commits == 1


def test_admin_can_delete_article():
    user = make_user(is_admin=True)
    article = make_article()
    fake_db = FakeDb(articles=[article], users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).delete("/api/v1/content/admin/articles/fastapi-payments")

    assert response.status_code == 204
    assert fake_db.articles == []
    assert fake_db.commits == 1

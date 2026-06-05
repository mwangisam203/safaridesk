from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.v1 import content
from app.core import dependencies
from app.db import session
from app.models.article import Article, ArticleTier
from app.models.free_article_read import FreeArticleRead
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import SubscriptionTier, User
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
        if isinstance(row, FreeArticleRead):
            self.free_reads.append(row)

    def commit(self):
        self.commits += 1

    def refresh(self, row):
        self.refreshed.append(row)

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


def make_article(tier=ArticleTier.BASIC):
    now = datetime.now(timezone.utc)
    return Article(
        id=10,
        title="Understanding FastAPI Payments",
        slug="fastapi-payments",
        summary="A practical payment flow overview.",
        body="This article explains the full subscription payment workflow.",
        tier=tier,
        author="SafariDesk Team",
        is_published=True,
        view_count=0,
        created_at=now,
        published_at=now,
    )


def make_user(tier=SubscriptionTier.FREE):
    return User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=tier,
        is_active=True,
        is_verified=False,
        is_admin=False,
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

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core import dependencies
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from app.core.rate_limit import reset_rate_limits
from app.core.config import settings
from jose import jwt
from app.api.v1 import auth as auth_api
from app.db import session
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import SubscriptionTier, User
from app.services import auth_service
from main import app


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def filter_by(self, **criteria):
        self.criteria.extend(criteria.items())
        return self

    def first(self):
        for row in self.rows:
            if all(self._matches(row, criterion) for criterion in self.criteria):
                return row
        return None

    def all(self):
        return [
            row for row in self.rows
            if all(self._matches(row, criterion) for criterion in self.criteria)
        ]

    def order_by(self, *args):
        return self

    def _matches(self, row, criterion):
        if isinstance(criterion, tuple):
            field, value = criterion
            return getattr(row, field) == value

        left = getattr(criterion, "left", None)
        right = getattr(criterion, "right", None)
        field = getattr(left, "key", None)
        value = getattr(right, "value", None)

        if field is None:
            return True

        return getattr(row, field) == value


class FakeDb:
    def __init__(self, users=None, subscriptions=None):
        self.users = users or []
        self.subscriptions = subscriptions or []
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, row):
        self.added.append(row)
        if isinstance(row, User):
            self.users.append(row)
        if isinstance(row, Subscription):
            self.subscriptions.append(row)

    def commit(self):
        self.commits += 1

    def refresh(self, row):
        self.refreshed.append(row)
        if row.id is None:
            row.id = len(self.users)
        if row.created_at is None:
            row.created_at = datetime.now(timezone.utc)
        if row.subscription_tier is None:
            row.subscription_tier = SubscriptionTier.FREE
        if row.is_active is None:
            row.is_active = True
        if row.is_verified is None:
            row.is_verified = False
        if row.is_admin is None:
            row.is_admin = False

    def query(self, model):
        if model is User:
            return FakeQuery(self.users)
        if model is Subscription:
            return FakeQuery(self.subscriptions)
        return FakeQuery([])

    def get(self, model, row_id):
        if model is User:
            return next((user for user in self.users if user.id == row_id), None)
        return None


class DummyTask:
    def __init__(self):
        self.calls = []

    def delay(self, *args):
        self.calls.append(args)


def make_user(
    user_id=7,
    email="sam@example.com",
    phone_number="+254700000001",
    password="strongpass123",
    is_active=True,
    is_verified=False,
    is_admin=False,
):
    return User(
        id=user_id,
        email=email,
        phone_number=phone_number,
        hashed_password=hash_password(password),
        full_name="Samson",
        subscription_tier=SubscriptionTier.FREE,
        is_active=is_active,
        is_verified=is_verified,
        is_admin=is_admin,
        created_at=datetime.now(timezone.utc),
    )


def make_client(fake_db):
    app.dependency_overrides[session.get_db] = lambda: fake_db
    return TestClient(app)


def teardown_function():
    reset_rate_limits()
    app.dependency_overrides.clear()


def setup_function():
    reset_rate_limits()


def test_register_creates_user_and_queues_verification_email(monkeypatch):
    fake_db = FakeDb()
    verification_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_verification_for_user",
        lambda user_id: verification_calls.append(user_id),
    )

    response = make_client(fake_db).post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "phone_number": "0712345678",
            "full_name": "New User",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 201
    assert response.json()["phone_number"] == "+254712345678"
    assert fake_db.users[0].email == "new@example.com"
    assert fake_db.users[0].hashed_password != "strongpass123"
    assert fake_db.users[0].is_verified is False
    assert fake_db.commits == 1
    assert verification_calls == [1]


def test_register_rejects_duplicate_email():
    fake_db = FakeDb(users=[make_user(email="taken@example.com")])

    response = make_client(fake_db).post(
        "/api/v1/auth/register",
        json={
            "email": "taken@example.com",
            "phone_number": "0712345678",
            "full_name": "New User",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"
    assert fake_db.commits == 0


def test_register_rejects_duplicate_phone_number():
    fake_db = FakeDb(users=[make_user(phone_number="+254712345678")])

    response = make_client(fake_db).post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "phone_number": "0712345678",
            "full_name": "New User",
            "password": "strongpass123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Phone number already registered"
    assert fake_db.commits == 0


def test_register_rate_limit_returns_retry_after(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(auth_api, "send_verification_for_user", lambda user_id: None)
    client = make_client(fake_db)

    for index in range(5):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"new{index}@example.com",
                "phone_number": f"07123456{index:02d}",
                "full_name": "New User",
                "password": "strongpass123",
            },
        )
        assert response.status_code == 201

    blocked = client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked@example.com",
            "phone_number": "0712345699",
            "full_name": "Blocked User",
            "password": "strongpass123",
        },
    )

    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many requests. Please try again shortly."
    assert "retry-after" in blocked.headers


def test_login_returns_tokens_for_valid_credentials():
    fake_db = FakeDb(users=[make_user(password="correctpass123")])

    response = make_client(fake_db).post(
        "/api/v1/auth/login",
        json={"email": "sam@example.com", "password": "correctpass123"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert decode_token(body["access_token"])["type"] == "access"
    assert decode_token(body["refresh_token"])["type"] == "refresh"


def test_refresh_rotates_token_pair():
    user = make_user(is_active=True)
    fake_db = FakeDb(users=[user])
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response = make_client(fake_db).post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    body = response.json()
    assert response.status_code == 200
    assert decode_token(body["access_token"])["type"] == "access"
    assert decode_token(body["refresh_token"])["type"] == "refresh"
    assert decode_token(body["access_token"])["sub"] == str(user.id)


def test_refresh_rejects_access_token():
    user = make_user()
    fake_db = FakeDb(users=[user])
    access_token = create_access_token({"sub": str(user.id)})

    response = make_client(fake_db).post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_rejects_inactive_user():
    user = make_user(is_active=False)
    fake_db = FakeDb(users=[user])
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response = make_client(fake_db).post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is deactivated"


def test_me_rejects_refresh_token():
    user = make_user()
    fake_db = FakeDb(users=[user])
    refresh_token = create_refresh_token({"sub": str(user.id)})

    response = make_client(fake_db).get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401


def test_login_rejects_wrong_password():
    fake_db = FakeDb(users=[make_user(password="correctpass123")])

    response = make_client(fake_db).post(
        "/api/v1/auth/login",
        json={"email": "sam@example.com", "password": "wrongpass123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_inactive_user():
    fake_db = FakeDb(users=[make_user(password="correctpass123", is_active=False)])

    response = make_client(fake_db).post(
        "/api/v1/auth/login",
        json={"email": "sam@example.com", "password": "correctpass123"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is deactivated"


def test_me_requires_authentication():
    response = make_client(FakeDb()).get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token():
    response = make_client(FakeDb()).get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_verify_email_marks_user_verified():
    user = make_user()
    fake_db = FakeDb(users=[user])
    token = create_email_verification_token(user.id)

    response = make_client(fake_db).get(
        "/api/v1/auth/verify-email",
        params={"token": token},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Email verified successfully.",
        "is_verified": True,
    }
    assert user.is_verified is True
    assert fake_db.commits == 1


def test_verify_email_rejects_access_token():
    user = make_user()
    fake_db = FakeDb(users=[user])
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(user.id)})
    response = make_client(fake_db).get(
        "/api/v1/auth/verify-email",
        params={"token": token},
    )

    assert response.status_code == 400
    assert user.is_verified is False


def test_verify_email_rejects_expired_token():
    user = make_user()
    fake_db = FakeDb(users=[user])
    token = jwt.encode(
        {
            "sub": str(user.id),
            "purpose": "email_verification",
            "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = make_client(fake_db).get(
        "/api/v1/auth/verify-email",
        params={"token": token},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification link."
    assert user.is_verified is False


def test_resend_verification_queues_email(monkeypatch):
    user = make_user()
    fake_db = FakeDb(users=[user])
    verification_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_verification_for_user",
        lambda user_id: verification_calls.append(user_id),
    )
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post("/api/v1/auth/resend-verification")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Verification email sent.",
        "is_verified": False,
    }
    assert verification_calls == [user.id]


def test_resend_verification_is_idempotent_for_verified_user(monkeypatch):
    user = make_user(is_verified=True)
    fake_db = FakeDb(users=[user])
    verification_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_verification_for_user",
        lambda user_id: verification_calls.append(user_id),
    )
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post("/api/v1/auth/resend-verification")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Email is already verified.",
        "is_verified": True,
    }
    assert verification_calls == []


def test_public_resend_verification_queues_email_without_login(monkeypatch):
    user = make_user(email="sam@example.com", is_verified=False)
    fake_db = FakeDb(users=[user])
    verification_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_verification_for_user",
        lambda user_id: verification_calls.append(user_id),
    )

    response = make_client(fake_db).post(
        "/api/v1/auth/resend-verification-email",
        json={"email": "sam@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith("If this account exists")
    assert verification_calls == [user.id]


def test_public_resend_verification_does_not_reveal_missing_email(monkeypatch):
    fake_db = FakeDb()
    verification_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_verification_for_user",
        lambda user_id: verification_calls.append(user_id),
    )

    response = make_client(fake_db).post(
        "/api/v1/auth/resend-verification-email",
        json={"email": "missing@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith("If this account exists")
    assert verification_calls == []


def test_public_resend_verification_can_send_directly(monkeypatch):
    user = make_user(email="sam@example.com", is_verified=False)
    fake_db = FakeDb(users=[user])
    direct_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_verification_for_user",
        lambda user_id: direct_calls.append(user_id),
    )

    response = make_client(fake_db).post(
        "/api/v1/auth/resend-verification-email",
        json={"email": "sam@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith("If this account exists")
    assert direct_calls == [user.id]


def test_forgot_password_queues_reset_email_without_revealing_account(monkeypatch):
    user = make_user(email="sam@example.com")
    fake_db = FakeDb(users=[user])
    reset_calls = []
    monkeypatch.setattr(
        auth_api,
        "send_password_reset_for_user",
        lambda user_id: reset_calls.append(user_id),
    )

    response = make_client(fake_db).post(
        "/api/v1/auth/forgot-password",
        json={"email": "sam@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"].startswith("If this account exists")
    assert reset_calls == [user.id]


def test_reset_password_updates_hash():
    user = make_user(password="oldpass123")
    fake_db = FakeDb(users=[user])
    token = create_password_reset_token(user.id)

    response = make_client(fake_db).post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "newpass123"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successfully. You can now sign in."
    assert fake_db.commits == 1
    assert auth_service.verify_password("newpass123", user.hashed_password)


def test_reset_password_rejects_verification_token():
    user = make_user(password="oldpass123")
    fake_db = FakeDb(users=[user])
    token = create_email_verification_token(user.id)

    response = make_client(fake_db).post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "newpass123"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired password reset link."


def test_logged_in_user_can_change_password():
    user = make_user(password="oldpass123", is_active=True)
    fake_db = FakeDb(users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully. Please sign in again."
    assert fake_db.commits == 1
    assert auth_service.verify_password("newpass123", user.hashed_password)


def test_change_password_rejects_wrong_current_password():
    user = make_user(password="oldpass123", is_active=True)
    fake_db = FakeDb(users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "wrongpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect."
    assert fake_db.commits == 0
    assert auth_service.verify_password("oldpass123", user.hashed_password)


def test_change_password_requires_matching_confirmation():
    user = make_user(password="oldpass123", is_active=True)
    fake_db = FakeDb(users=[user])
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = make_client(fake_db).post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "different123",
        },
    )

    assert response.status_code == 422
    assert fake_db.commits == 0


def test_admin_can_list_users():
    admin = make_user(user_id=1, email="admin@example.com", is_verified=True, is_admin=True)
    user = make_user(user_id=2, email="reader@example.com")
    fake_db = FakeDb(users=[admin, user])
    app.dependency_overrides[dependencies.require_admin] = lambda: admin

    response = make_client(fake_db).get("/api/v1/users/admin/users")

    assert response.status_code == 200
    assert [item["email"] for item in response.json()] == [
        "admin@example.com",
        "reader@example.com",
    ]


def test_admin_can_update_user_flags():
    admin = make_user(user_id=1, email="admin@example.com", is_verified=True, is_admin=True)
    user = make_user(user_id=2, email="reader@example.com", is_verified=False)
    fake_db = FakeDb(users=[admin, user])
    app.dependency_overrides[dependencies.require_admin] = lambda: admin

    response = make_client(fake_db).patch(
        f"/api/v1/users/admin/users/{user.id}",
        json={"is_verified": True, "is_active": False, "subscription_tier": "basic"},
    )

    assert response.status_code == 200
    assert response.json()["is_verified"] is True
    assert response.json()["is_active"] is False
    assert response.json()["subscription_tier"] == "basic"
    assert fake_db.subscriptions[0].user_id == user.id
    assert fake_db.subscriptions[0].tier == SubscriptionTierInfo.BASIC
    assert fake_db.subscriptions[0].status == SubscriptionStatus.ACTIVE
    assert fake_db.commits == 1


def test_admin_can_expire_subscription_by_setting_free_tier():
    admin = make_user(user_id=1, email="admin@example.com", is_verified=True, is_admin=True)
    user = make_user(user_id=2, email="reader@example.com", is_verified=True)
    user.subscription_tier = SubscriptionTier.PRO
    subscription = Subscription(
        id=8,
        user_id=user.id,
        tier=SubscriptionTierInfo.PRO,
        status=SubscriptionStatus.ACTIVE,
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc),
    )
    fake_db = FakeDb(users=[admin, user], subscriptions=[subscription])
    app.dependency_overrides[dependencies.require_admin] = lambda: admin

    response = make_client(fake_db).patch(
        f"/api/v1/users/admin/users/{user.id}",
        json={"subscription_tier": "free"},
    )

    assert response.status_code == 200
    assert response.json()["subscription_tier"] == "free"
    assert subscription.status == SubscriptionStatus.EXPIRED
    assert fake_db.commits == 1


def test_admin_cannot_remove_own_admin_access():
    admin = make_user(user_id=1, email="admin@example.com", is_verified=True, is_admin=True)
    fake_db = FakeDb(users=[admin])
    app.dependency_overrides[dependencies.require_admin] = lambda: admin

    response = make_client(fake_db).patch(
        f"/api/v1/users/admin/users/{admin.id}",
        json={"is_admin": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot remove your own admin access."

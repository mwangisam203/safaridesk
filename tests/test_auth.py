from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db import session
from app.models.user import SubscriptionTier, User
from main import app


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        return self

    def first(self):
        for row in self.rows:
            if all(self._matches(row, criterion) for criterion in self.criteria):
                return row
        return None

    def _matches(self, row, criterion):
        left = getattr(criterion, "left", None)
        right = getattr(criterion, "right", None)
        field = getattr(left, "key", None)
        value = getattr(right, "value", None)

        if field is None:
            return True

        return getattr(row, field) == value


class FakeDb:
    def __init__(self, users=None):
        self.users = users or []
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, row):
        self.added.append(row)
        if isinstance(row, User):
            self.users.append(row)

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
        return FakeQuery([])


def make_user(
    email="sam@example.com",
    phone_number="+254700000001",
    password="strongpass123",
    is_active=True,
):
    return User(
        id=7,
        email=email,
        phone_number=phone_number,
        hashed_password=hash_password(password),
        full_name="Samson",
        subscription_tier=SubscriptionTier.FREE,
        is_active=is_active,
        is_verified=False,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
    )


def make_client(fake_db):
    app.dependency_overrides[session.get_db] = lambda: fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_register_creates_user_with_normalized_phone_number():
    fake_db = FakeDb()

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
    assert fake_db.commits == 1


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

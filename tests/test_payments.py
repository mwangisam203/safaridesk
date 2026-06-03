from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.v1 import payments
from app.core import dependencies
from app.db import session
from app.models.subscription import SubscriptionTierInfo
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import SubscriptionTier, User
from main import app


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.criteria = {}

    def filter_by(self, **criteria):
        self.criteria = criteria
        return self

    def first(self):
        for row in self.rows:
            if all(getattr(row, key) == value for key, value in self.criteria.items()):
                return row
        return None


class FakeDb:
    def __init__(self, transactions=None):
        self.transactions = transactions or []
        self.commits = 0

    def add(self, row):
        self.transactions.append(row)

    def commit(self):
        self.commits += 1

    def query(self, model):
        if model is Transaction:
            return FakeQuery(self.transactions)
        return FakeQuery([])


class DummyTask:
    def __init__(self):
        self.calls = []

    def delay(self, *args):
        self.calls.append(args)


def make_user():
    user = User(
        id=7,
        email="sam@example.com",
        phone_number="+254700000001",
        hashed_password="hashed",
        full_name="Samson",
        subscription_tier=SubscriptionTier.FREE,
    )
    return user


def make_client(fake_db):
    app.dependency_overrides[dependencies.get_current_user] = make_user
    app.dependency_overrides[session.get_db] = lambda: fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_stk_push_uses_custom_payment_phone(monkeypatch):
    fake_db = FakeDb()
    captured = {}

    async def fake_stk_push(**kwargs):
        captured.update(kwargs)
        return {
            "ResponseCode": "0",
            "ResponseDescription": "Success",
            "CheckoutRequestID": "ws_CO_123",
            "MerchantRequestID": "merchant_123",
        }

    monkeypatch.setattr(payments.mpesa, "initiate_stk_push", fake_stk_push)

    response = make_client(fake_db).post(
        "/api/v1/payments/stk-push",
        json={"tier": "basic", "phone_number": "0712345678"},
    )

    assert response.status_code == 200
    assert captured["phone"] == "+254712345678"
    assert fake_db.transactions[0].phone_number == "+254712345678"
    assert fake_db.transactions[0].status == TransactionStatus.PENDING
    assert fake_db.transactions[0].transaction_type == TransactionType.SUBSCRIPTION_PAYMENT


def test_stk_push_defaults_to_registered_phone(monkeypatch):
    fake_db = FakeDb()
    captured = {}

    async def fake_stk_push(**kwargs):
        captured.update(kwargs)
        return {
            "ResponseCode": "0",
            "ResponseDescription": "Success",
            "CheckoutRequestID": "ws_CO_456",
            "MerchantRequestID": "merchant_456",
        }

    monkeypatch.setattr(payments.mpesa, "initiate_stk_push", fake_stk_push)

    response = make_client(fake_db).post(
        "/api/v1/payments/stk-push",
        json={"tier": "pro"},
    )

    assert response.status_code == 200
    assert captured["phone"] == "+254700000001"
    assert fake_db.transactions[0].phone_number == "+254700000001"


def test_success_callback_completes_transaction_and_activates_subscription(monkeypatch):
    txn = Transaction(
        user_id=7,
        mpesa_request_id="ws_CO_success",
        merchant_request_id="merchant_success",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number="+254712345678",
    )
    fake_db = FakeDb([txn])
    activated = []
    confirmation_task = DummyTask()

    class FakeSubscriptionService:
        def __init__(self, db):
            self.db = db

        def activate(self, user_id, tier):
            activated.append((user_id, tier))

    monkeypatch.setattr(payments, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(
        "app.tasks.email_tasks.send_payment_confirmation",
        confirmation_task,
    )

    response = make_client(fake_db).post(
        "/api/v1/payments/mpesa-callback",
        json={
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_success",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "MpesaReceiptNumber", "Value": "TST123"},
                        ]
                    },
                }
            }
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ResultCode": 0, "ResultDesc": "Accepted"}
    assert txn.status == TransactionStatus.COMPLETED
    assert txn.mpesa_receipt_number == "TST123"
    assert txn.completed_at is not None
    assert activated == [(7, "basic")]
    assert confirmation_task.calls == [(7, "TST123", "1.00")]


def test_failed_callback_marks_transaction_failed(monkeypatch):
    txn = Transaction(
        user_id=7,
        mpesa_request_id="ws_CO_failed",
        merchant_request_id="merchant_failed",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number="+254712345678",
    )
    fake_db = FakeDb([txn])
    failed_task = DummyTask()
    monkeypatch.setattr("app.tasks.email_tasks.send_payment_failed", failed_task)

    response = make_client(fake_db).post(
        "/api/v1/payments/mpesa-callback",
        json={
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_failed",
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user",
                }
            }
        },
    )

    assert response.status_code == 200
    assert txn.status == TransactionStatus.FAILED
    assert txn.failure_reason == "Request cancelled by user"
    assert failed_task.calls == [(7, "1.00", "Request cancelled by user")]

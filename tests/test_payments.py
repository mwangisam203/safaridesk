from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.v1 import payments
from app.core import dependencies
from app.db import session
from app.tasks import reconciler_task
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
        is_verified=True,
    )
    return user


def make_client(fake_db):
    app.dependency_overrides[dependencies.get_current_user] = make_user
    app.dependency_overrides[session.get_db] = lambda: fake_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_lists_subscription_plans():
    response = make_client(FakeDb()).get("/api/v1/payments/plans")

    assert response.status_code == 200
    assert response.json() == {
        "plans": [
            {
                "tier": "basic",
                "amount": 1,
                "original_amount": 1,
                "credit_applied": 0,
                "billing_mode": "new",
                "currency": "KES",
                "duration_days": 30,
            },
            {
                "tier": "pro",
                "amount": 5,
                "original_amount": 5,
                "credit_applied": 0,
                "billing_mode": "new",
                "currency": "KES",
                "duration_days": 30,
            },
        ]
    }


def test_unverified_user_cannot_start_payment():
    user = make_user()
    user.is_verified = False
    fake_db = FakeDb()
    client = make_client(fake_db)
    app.dependency_overrides[dependencies.get_current_user] = lambda: user

    response = client.post(
        "/api/v1/payments/stk-push",
        json={"tier": "basic"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Verify your email before continuing."
    assert fake_db.transactions == []


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


def test_payment_status_returns_pending_for_current_user():
    txn = Transaction(
        user_id=7,
        mpesa_request_id="ws_CO_pending",
        merchant_request_id="merchant_pending",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number="+254712345678",
    )

    response = make_client(FakeDb([txn])).get("/api/v1/payments/status/ws_CO_pending")

    assert response.status_code == 200
    assert response.json() == {
        "checkout_request_id": "ws_CO_pending",
        "status": "pending",
        "message": "Waiting for M-Pesa confirmation.",
        "tier": "basic",
        "receipt_number": None,
        "failure_reason": None,
    }


def test_payment_status_returns_completed_receipt_for_current_user():
    txn = Transaction(
        user_id=7,
        mpesa_request_id="ws_CO_done",
        merchant_request_id="merchant_done",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.COMPLETED,
        phone_number="+254712345678",
        mpesa_receipt_number="TST123",
    )

    response = make_client(FakeDb([txn])).get("/api/v1/payments/status/ws_CO_done")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["receipt_number"] == "TST123"
    assert response.json()["message"] == "Payment confirmed. Your BASIC subscription is active."


def test_payment_status_does_not_expose_other_users_payment():
    txn = Transaction(
        user_id=99,
        mpesa_request_id="ws_CO_other",
        merchant_request_id="merchant_other",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number="+254712345678",
    )

    response = make_client(FakeDb([txn])).get("/api/v1/payments/status/ws_CO_other")

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment request not found."


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
    sms_task = DummyTask()

    class FakeSubscriptionService:
        def __init__(self, db):
            self.db = db

        def activate(self, user_id, tier, amount_paid=None):
            activated.append((user_id, tier))

    monkeypatch.setattr(payments, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(
        "app.tasks.email_tasks.send_payment_confirmation",
        confirmation_task,
    )
    monkeypatch.setattr(
        "app.tasks.sms_tasks.send_payment_confirmation_sms",
        sms_task,
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
    assert sms_task.calls == [(7, "1.00")]


def test_success_callback_activates_selected_pro_subscription(monkeypatch):
    txn = Transaction(
        user_id=7,
        mpesa_request_id="ws_CO_pro_success",
        merchant_request_id="merchant_pro_success",
        amount=Decimal("5.00"),
        tier=SubscriptionTierInfo.PRO,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number="+254712345678",
    )
    fake_db = FakeDb([txn])
    activated = []
    confirmation_task = DummyTask()
    sms_task = DummyTask()

    class FakeSubscriptionService:
        def __init__(self, db):
            self.db = db

        def activate(self, user_id, tier, amount_paid=None):
            activated.append((user_id, tier))

    monkeypatch.setattr(payments, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(
        "app.tasks.email_tasks.send_payment_confirmation",
        confirmation_task,
    )
    monkeypatch.setattr(
        "app.tasks.sms_tasks.send_payment_confirmation_sms",
        sms_task,
    )

    response = make_client(fake_db).post(
        "/api/v1/payments/mpesa-callback",
        json={
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_pro_success",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "MpesaReceiptNumber", "Value": "PRO123"},
                        ]
                    },
                }
            }
        },
    )

    assert response.status_code == 200
    assert txn.status == TransactionStatus.COMPLETED
    assert txn.mpesa_receipt_number == "PRO123"
    assert activated == [(7, "pro")]
    assert confirmation_task.calls == [(7, "PRO123", "5.00")]
    assert sms_task.calls == [(7, "5.00")]


def test_late_success_callback_backfills_receipt_without_duplicate_activation(monkeypatch):
    txn = Transaction(
        user_id=7,
        mpesa_request_id="ws_CO_reconciled",
        merchant_request_id="merchant_reconciled",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.COMPLETED,
        phone_number="+254712345678",
    )
    fake_db = FakeDb([txn])
    confirmation_task = DummyTask()

    class FailIfCalledSubscriptionService:
        def __init__(self, db):
            self.db = db

        def activate(self, user_id, tier, amount_paid=None):
            raise AssertionError("completed callback should not reactivate subscription")

    monkeypatch.setattr(payments, "SubscriptionService", FailIfCalledSubscriptionService)
    monkeypatch.setattr(
        "app.tasks.email_tasks.send_payment_confirmation",
        confirmation_task,
    )

    response = make_client(fake_db).post(
        "/api/v1/payments/mpesa-callback",
        json={
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_reconciled",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "MpesaReceiptNumber", "Value": "LATE123"},
                        ]
                    },
                }
            }
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ResultCode": 0, "ResultDesc": "Accepted"}
    assert txn.status == TransactionStatus.COMPLETED
    assert txn.mpesa_receipt_number == "LATE123"
    assert txn.raw_callback is not None
    assert fake_db.commits == 1
    assert confirmation_task.calls == []


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


def test_reconciler_skips_already_processed_transaction():
    txn = Transaction(
        id=12,
        user_id=7,
        mpesa_request_id="ws_CO_done",
        merchant_request_id="merchant_done",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.COMPLETED,
        phone_number="+254712345678",
    )
    fake_db = FakeDb([txn])

    class FailIfCalledMpesa:
        async def query_stk_status(self, checkout_request_id):
            raise AssertionError("reconciler should not query non-pending transactions")

    reconciler_task._reconcile_single(txn, fake_db, FailIfCalledMpesa())

    assert fake_db.commits == 0
    assert txn.status == TransactionStatus.COMPLETED


def test_reconciler_completes_pending_transaction_and_persists_status(monkeypatch):
    txn = Transaction(
        id=13,
        user_id=7,
        mpesa_request_id="ws_CO_pending",
        merchant_request_id="merchant_pending",
        amount=Decimal("1.00"),
        tier=SubscriptionTierInfo.BASIC,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number="+254712345678",
    )
    fake_db = FakeDb([txn])
    activated = []
    confirmation_task = DummyTask()
    sms_task = DummyTask()

    class FakeMpesa:
        async def query_stk_status(self, checkout_request_id):
            return {
                "ResultCode": "0",
                "ResultDesc": "The service request is processed successfully.",
            }

    class FakeSubscriptionService:
        def __init__(self, db):
            self.db = db

        def activate(self, user_id, tier, amount_paid=None):
            activated.append((user_id, tier))

    monkeypatch.setattr(reconciler_task, "SubscriptionService", FakeSubscriptionService)
    monkeypatch.setattr(reconciler_task, "send_payment_confirmation", confirmation_task)
    monkeypatch.setattr(reconciler_task, "send_payment_confirmation_sms", sms_task)

    reconciler_task._reconcile_single(txn, fake_db, FakeMpesa())

    assert txn.status == TransactionStatus.COMPLETED
    assert txn.mpesa_receipt_number is None
    assert txn.mpesa_response_code == "0"
    assert txn.mpesa_response_description == "The service request is processed successfully."
    assert txn.raw_callback["ResultCode"] == "0"
    assert txn.completed_at is not None
    assert activated == [(7, "basic")]
    assert confirmation_task.calls == [(7, None, "1.00")]
    assert sms_task.calls == [(7, "1.00")]

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_verified_user
from app.core.observability import client_ip, log_event
from app.core.rate_limit import rate_limit
from app.core.security import decode_token
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.services.mpesa_service import MpesaService
from app.services.notification_service import notify_payment_completed, notify_payment_failed
from app.services.subscription_service import SubscriptionService, TIER_PRICES
from app.schemas.payments import PaymentStatusResponse, STKPushRequest, STKPushResponse
#from app.core.audit import log_action  #
import logging

router = APIRouter(prefix="/payments", tags=["Payments"])
mpesa  = MpesaService()
logger = logging.getLogger(__name__)

DIRECT_RECONCILE_AFTER_SECONDS = 45
DIRECT_RECONCILE_COOLDOWN_SECONDS = 60
DIRECT_RECONCILE_MAX_ATTEMPTS = 3


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def _extract_callback_metadata(stk_callback: dict) -> dict:
    items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
    return {item["Name"]: item.get("Value") for item in items}


def _backfill_completed_receipt(txn: Transaction, stk_callback: dict, payload: dict, db: Session) -> None:
    """
    If the reconciler completed a payment before the real callback arrived, the
    transaction may be completed without a receipt. Backfill receipt/callback
    data without re-activating the subscription or sending duplicate email.
    """
    if txn.status != TransactionStatus.COMPLETED:
        return

    meta = _extract_callback_metadata(stk_callback)
    receipt_number = meta.get("MpesaReceiptNumber")
    changed = False

    if receipt_number and not txn.mpesa_receipt_number:
        txn.mpesa_receipt_number = receipt_number
        changed = True

    if not txn.raw_callback:
        txn.raw_callback = payload
        changed = True

    if changed:
        db.commit()


def _payment_status_response(
    checkout_request_id: str,
    txn: Transaction,
    db: Session,
    user_id: int,
) -> PaymentStatusResponse:
    tier = txn.tier.value if txn.tier else None
    if txn.status == TransactionStatus.COMPLETED:
        scheduled = (
            db.query(Subscription)
            .filter_by(
                user_id=user_id,
                tier=txn.tier,
                status=SubscriptionStatus.PENDING,
            )
            .first()
            if txn.tier
            else None
        )
        if scheduled:
            starts_at = scheduled.started_at
            starts_text = starts_at.strftime("%d %b %Y") if starts_at else "after your current plan ends"
            return PaymentStatusResponse(
                checkout_request_id=checkout_request_id,
                status=txn.status.value,
                tier=tier,
                receipt_number=txn.mpesa_receipt_number,
                message=f"Payment confirmed. Your {tier.upper()} subscription starts on {starts_text}.",
            )

        return PaymentStatusResponse(
            checkout_request_id=checkout_request_id,
            status=txn.status.value,
            tier=tier,
            receipt_number=txn.mpesa_receipt_number,
            message=f"Payment confirmed. Your {tier.upper() if tier else 'paid'} subscription is active.",
        )

    if txn.status in {TransactionStatus.FAILED, TransactionStatus.CANCELLED}:
        return PaymentStatusResponse(
            checkout_request_id=checkout_request_id,
            status=txn.status.value,
            tier=tier,
            failure_reason=txn.failure_reason,
            message=txn.failure_reason or "Payment was not completed.",
        )

    return PaymentStatusResponse(
        checkout_request_id=checkout_request_id,
        status=txn.status.value,
        tier=tier,
        message="Waiting for M-Pesa confirmation.",
    )


def _should_direct_reconcile(txn: Transaction, now: datetime) -> tuple[bool, str | None]:
    if txn.status != TransactionStatus.PENDING:
        return False, "not_pending"

    attempts = getattr(txn, "reconcile_attempts", 0) or 0
    if attempts >= DIRECT_RECONCILE_MAX_ATTEMPTS:
        return False, "max_attempts"

    initiated_at = _aware_utc(getattr(txn, "initiated_at", None))
    if initiated_at and now - initiated_at < timedelta(seconds=DIRECT_RECONCILE_AFTER_SECONDS):
        return False, "too_new"

    last_reconciled_at = _aware_utc(getattr(txn, "last_reconciled_at", None))
    if last_reconciled_at and now - last_reconciled_at < timedelta(seconds=DIRECT_RECONCILE_COOLDOWN_SECONDS):
        return False, "cooldown"

    return True, None


def _record_direct_reconcile_attempt(txn: Transaction, db: Session, now: datetime) -> None:
    txn.reconcile_attempts = (getattr(txn, "reconcile_attempts", 0) or 0) + 1
    txn.last_reconciled_at = now
    db.commit()


def _apply_direct_reconcile_result(txn: Transaction, result: dict, db: Session) -> bool:
    result_code = str(result.get("ResultCode", ""))
    result_desc = result.get("ResultDesc", "Unknown")

    txn.raw_callback = result
    txn.mpesa_response_code = result_code
    txn.mpesa_response_description = result_desc

    if not result_code:
        db.commit()
        return False

    if result_code == "0":
        txn.status = TransactionStatus.COMPLETED
        txn.completed_at = datetime.now(timezone.utc)
        txn.failure_reason = None
        txn.mpesa_receipt_number = (
            result.get("MpesaReceiptNumber")
            or result.get("ReceiptNumber")
            or txn.mpesa_receipt_number
        )
        db.commit()
        SubscriptionService(db).activate(txn.user_id, txn.tier.value, amount_paid=txn.amount)
        notify_payment_completed(
            db,
            user_id=txn.user_id,
            transaction_id=txn.id,
            tier=txn.tier.value,
            amount=str(txn.amount),
        )
        return True

    if result_code == "1032":
        txn.status = TransactionStatus.CANCELLED
        txn.failure_reason = "Request cancelled by user"
    elif result_code in ("1037", "1001"):
        reason_map = {
            "1037": "Payment timed out. Please try again.",
            "1001": "Insufficient M-Pesa balance.",
        }
        txn.status = TransactionStatus.FAILED
        txn.failure_reason = reason_map.get(result_code, result_desc)
    else:
        txn.status = TransactionStatus.FAILED
        txn.failure_reason = result_desc

    db.commit()
    notify_payment_failed(
        db,
        user_id=txn.user_id,
        transaction_id=txn.id,
        reason=txn.failure_reason,
        cancelled=txn.status == TransactionStatus.CANCELLED,
    )
    return True


@router.get("/plans")
def list_subscription_plans(
    request: Request,
    db: Session = Depends(get_db),
):
    user = None
    token = request.headers.get("Authorization")
    if token:
        try:
            payload = decode_token(token.replace("Bearer ", ""))
            if payload.get("type") == "access":
                user = db.get(User, int(payload["sub"]))
        except Exception:
            user = None

    service = SubscriptionService(db)
    basic_quote = service.quote(user.id, "basic") if user else None
    pro_quote = service.quote(user.id, "pro") if user else None

    return {
        "plans": [
            {
                "tier": "basic",
                "amount": basic_quote["amount"] if basic_quote else int(TIER_PRICES["basic"]),
                "original_amount": int(TIER_PRICES["basic"]),
                "credit_applied": float(basic_quote["credit_applied"]) if basic_quote else 0,
                "billing_mode": basic_quote["mode"] if basic_quote else "new",
                "starts_at": basic_quote["starts_at"] if basic_quote else None,
                "current_tier": basic_quote["current_tier"] if basic_quote else None,
                "currency": "KES",
                "duration_days": 30,
            },
            {
                "tier": "pro",
                "amount": pro_quote["amount"] if pro_quote else int(TIER_PRICES["pro"]),
                "original_amount": int(TIER_PRICES["pro"]),
                "credit_applied": float(pro_quote["credit_applied"]) if pro_quote else 0,
                "billing_mode": pro_quote["mode"] if pro_quote else "new",
                "starts_at": pro_quote["starts_at"] if pro_quote else None,
                "current_tier": pro_quote["current_tier"] if pro_quote else None,
                "currency": "KES",
                "duration_days": 30,
            },
        ]
    }


@router.post(
    "/stk-push",
    response_model=STKPushResponse,
    dependencies=[Depends(rate_limit("payments:stk-push", limit=5, window_seconds=600))],
)
async def initiate_payment(
    body: STKPushRequest,
    request: Request,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    tier = SubscriptionTierInfo(body.tier.value)
    amount = SubscriptionService(db).quote(current_user.id, tier.value)["amount"]
    payment_phone = body.phone_number or current_user.phone_number

    log_event(
        logger,
        logging.INFO,
        "payment.stk_push.requested",
        user_id=current_user.id,
        tier=tier,
        amount=amount,
        phone_provided=bool(body.phone_number),
        client_ip=client_ip(request),
    )

    try:
        result = await mpesa.initiate_stk_push(
            phone=payment_phone,
            amount=amount,
            account_ref="SAFARIDESK-SUB",
            description=f"{tier.value.upper()} subscription",
        )
    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "payment.stk_push.provider_error",
            user_id=current_user.id,
            tier=tier,
            amount=amount,
            error_type=type(e).__name__,
            error=str(e),
            client_ip=client_ip(request),
        )
        raise HTTPException(502, "M-Pesa request failed. Try again.")

    if result.get("ResponseCode") != "0":
        log_event(
            logger,
            logging.WARNING,
            "payment.stk_push.rejected",
            user_id=current_user.id,
            tier=tier,
            amount=amount,
            response_code=result.get("ResponseCode"),
            response_description=result.get("ResponseDescription"),
            client_ip=client_ip(request),
        )
        raise HTTPException(400, result.get("ResponseDescription", "STK Push rejected"))

    # Persist pending transaction
    txn = Transaction(
        user_id=current_user.id,
        mpesa_request_id=result["CheckoutRequestID"],
        merchant_request_id=result["MerchantRequestID"],
        amount=amount,
        tier=tier,
        transaction_type=TransactionType.SUBSCRIPTION_PAYMENT,
        status=TransactionStatus.PENDING,
        phone_number=payment_phone,
        mpesa_response_code=result.get("ResponseCode"),
        mpesa_response_description=result.get("ResponseDescription"),
    )
    db.add(txn)
    db.commit()

    log_event(
        logger,
        logging.INFO,
        "payment.stk_push.accepted",
        user_id=current_user.id,
        transaction_id=txn.id,
        checkout_request_id=txn.mpesa_request_id,
        merchant_request_id=txn.merchant_request_id,
        tier=tier,
        amount=amount,
    )

    return STKPushResponse(
        checkout_request_id=result["CheckoutRequestID"],
        merchant_request_id=result["MerchantRequestID"],
        message="Check your phone and enter your M-Pesa PIN.",
    )


@router.get("/status/{checkout_request_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    checkout_request_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter_by(
        mpesa_request_id=checkout_request_id,
        user_id=current_user.id,
    ).first()

    if not txn:
        raise HTTPException(404, "Payment request not found.")

    now = datetime.now(timezone.utc)
    should_reconcile, skipped_reason = _should_direct_reconcile(txn, now)
    if should_reconcile:
        _record_direct_reconcile_attempt(txn, db, now)
        log_event(
            logger,
            logging.INFO,
            "payment.status_reconcile.started",
            transaction_id=txn.id,
            user_id=current_user.id,
            checkout_request_id=checkout_request_id,
            attempt=txn.reconcile_attempts,
        )
        try:
            result = await mpesa.query_stk_status(checkout_request_id)
        except Exception as exc:
            log_event(
                logger,
                logging.WARNING,
                "payment.status_reconcile.provider_error",
                transaction_id=txn.id,
                user_id=current_user.id,
                checkout_request_id=checkout_request_id,
                attempt=txn.reconcile_attempts,
                error_type=type(exc).__name__,
                error=str(exc),
            )
        else:
            changed = _apply_direct_reconcile_result(txn, result, db)
            log_event(
                logger,
                logging.INFO,
                "payment.status_reconcile.completed",
                transaction_id=txn.id,
                user_id=current_user.id,
                checkout_request_id=checkout_request_id,
                attempt=txn.reconcile_attempts,
                result_code=result.get("ResultCode"),
                transaction_status=txn.status,
                changed=changed,
            )
    elif txn.status == TransactionStatus.PENDING:
        log_event(
            logger,
            logging.DEBUG,
            "payment.status_reconcile.skipped",
            transaction_id=txn.id,
            user_id=current_user.id,
            checkout_request_id=checkout_request_id,
            reason=skipped_reason,
            attempts=getattr(txn, "reconcile_attempts", 0) or 0,
        )

    return _payment_status_response(checkout_request_id, txn, db, current_user.id)


@router.post("/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    """
    Safaricom posts here. Must always return 200 or they retry.
    """
    try:
        payload = await request.json()
        stk_callback = payload["Body"]["stkCallback"]
        checkout_id  = stk_callback["CheckoutRequestID"]
        result_code  = stk_callback["ResultCode"]

        log_event(
            logger,
            logging.INFO,
            "payment.callback.received",
            checkout_request_id=checkout_id,
            result_code=result_code,
            result_description=stk_callback.get("ResultDesc"),
            client_ip=client_ip(request),
        )

        txn = db.query(Transaction).filter_by(
            mpesa_request_id=checkout_id
        ).first()

        if not txn:
            log_event(
                logger,
                logging.WARNING,
                "payment.callback.unknown_checkout",
                checkout_request_id=checkout_id,
                result_code=result_code,
            )
            return {"ResultCode": 0, "ResultDesc": "Accepted"}  # unknown, ignore

        if txn.status != TransactionStatus.PENDING:
            if result_code == 0:
                _backfill_completed_receipt(txn, stk_callback, payload, db)
            log_event(
                logger,
                logging.INFO,
                "payment.callback.idempotent_skip",
                transaction_id=txn.id,
                user_id=txn.user_id,
                checkout_request_id=checkout_id,
                transaction_status=txn.status,
                result_code=result_code,
            )
            return {"ResultCode": 0, "ResultDesc": "Accepted"}  # idempotency guard

        txn.raw_callback = payload
        txn.mpesa_response_code = str(result_code)
        txn.mpesa_response_description = stk_callback.get("ResultDesc")

        if result_code == 0:
            # Extract M-Pesa receipt from metadata
            meta = _extract_callback_metadata(stk_callback)

            txn.status = TransactionStatus.COMPLETED
            txn.mpesa_receipt_number = meta.get("MpesaReceiptNumber")
            txn.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Upgrade subscription
            SubscriptionService(db).activate(txn.user_id, txn.tier.value, amount_paid=txn.amount)
            notify_payment_completed(
                db,
                user_id=txn.user_id,
                transaction_id=txn.id,
                tier=txn.tier.value,
                amount=str(txn.amount),
            )

            # Fire-and-forget email (Celery)
            from app.tasks.email_tasks import send_payment_confirmation
            from app.tasks.sms_tasks import send_payment_confirmation_sms
            send_payment_confirmation.delay(txn.user_id, txn.mpesa_receipt_number, str(txn.amount))
            send_payment_confirmation_sms.delay(txn.user_id, str(txn.amount))
            log_event(
                logger,
                logging.INFO,
                "payment.callback.completed",
                transaction_id=txn.id,
                user_id=txn.user_id,
                checkout_request_id=checkout_id,
                tier=txn.tier,
                amount=txn.amount,
                receipt_present=bool(txn.mpesa_receipt_number),
            )

        else:
            txn.status = TransactionStatus.FAILED
            txn.failure_reason = stk_callback.get("ResultDesc")
            db.commit()
            notify_payment_failed(
                db,
                user_id=txn.user_id,
                transaction_id=txn.id,
                reason=txn.failure_reason,
                cancelled=False,
            )

            from app.tasks.email_tasks import send_payment_failed
            send_payment_failed.delay(txn.user_id, str(txn.amount), txn.failure_reason)
            log_event(
                logger,
                logging.WARNING,
                "payment.callback.failed",
                transaction_id=txn.id,
                user_id=txn.user_id,
                checkout_request_id=checkout_id,
                result_code=result_code,
                failure_reason=txn.failure_reason,
            )

    except Exception as e:
        log_event(
            logger,
            logging.ERROR,
            "payment.callback.processing_error",
            error_type=type(e).__name__,
            error=str(e),
            client_ip=client_ip(request),
        )
        # Still return 200 — never let Safaricom see a 5xx

    return {"ResultCode": 0, "ResultDesc": "Accepted"}

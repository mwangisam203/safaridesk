from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_verified_user
from app.core.rate_limit import rate_limit
from app.core.security import decode_token
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionTierInfo
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.services.mpesa_service import MpesaService
from app.services.subscription_service import SubscriptionService, TIER_PRICES
from app.schemas.payments import PaymentStatusResponse, STKPushRequest, STKPushResponse
#from app.core.audit import log_action  #
import logging

router = APIRouter(prefix="/payments", tags=["Payments"])
mpesa  = MpesaService()

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
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    tier = SubscriptionTierInfo(body.tier.value)
    amount = SubscriptionService(db).quote(current_user.id, tier.value)["amount"]
    payment_phone = body.phone_number or current_user.phone_number

    try:
        result = await mpesa.initiate_stk_push(
            phone=payment_phone,
            amount=amount,
            account_ref="SAFARIDESK-SUB",
            description=f"{tier.value.upper()} subscription",
        )
    except Exception as e:
        logging.error(f"STK Push failed: {e}")
        raise HTTPException(502, "M-Pesa request failed. Try again.")

    if result.get("ResponseCode") != "0":
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

    return STKPushResponse(
        checkout_request_id=result["CheckoutRequestID"],
        merchant_request_id=result["MerchantRequestID"],
        message="Check your phone and enter your M-Pesa PIN.",
    )


@router.get("/status/{checkout_request_id}", response_model=PaymentStatusResponse)
def get_payment_status(
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

    tier = txn.tier.value if txn.tier else None
    if txn.status == TransactionStatus.COMPLETED:
        scheduled = (
            db.query(Subscription)
            .filter_by(
                user_id=current_user.id,
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

        txn = db.query(Transaction).filter_by(
            mpesa_request_id=checkout_id
        ).first()

        if not txn:
            return {"ResultCode": 0, "ResultDesc": "Accepted"}  # unknown, ignore

        if txn.status != TransactionStatus.PENDING:
            if result_code == 0:
                _backfill_completed_receipt(txn, stk_callback, payload, db)
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

            # Fire-and-forget email (Celery)
            from app.tasks.email_tasks import send_payment_confirmation
            from app.tasks.sms_tasks import send_payment_confirmation_sms
            send_payment_confirmation.delay(txn.user_id, txn.mpesa_receipt_number, str(txn.amount))
            send_payment_confirmation_sms.delay(txn.user_id, str(txn.amount))

        else:
            txn.status = TransactionStatus.FAILED
            txn.failure_reason = stk_callback.get("ResultDesc")
            db.commit()

            from app.tasks.email_tasks import send_payment_failed
            send_payment_failed.delay(txn.user_id, str(txn.amount), txn.failure_reason)

    except Exception as e:
        logging.error(f"Callback processing error: {e}")
        # Still return 200 — never let Safaricom see a 5xx

    return {"ResultCode": 0, "ResultDesc": "Accepted"}

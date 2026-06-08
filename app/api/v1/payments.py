from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import require_verified_user
from app.models.subscription import SubscriptionTierInfo
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.services.mpesa_service import MpesaService
from app.services.subscription_service import SubscriptionService
from app.schemas.payments import STKPushRequest, STKPushResponse
#from app.core.audit import log_action  #
import logging

router = APIRouter(prefix="/payments", tags=["Payments"])
mpesa  = MpesaService()

TIER_PRICES = {"basic": 1, "pro": 5}   # KES


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
def list_subscription_plans():
    return {
        "plans": [
            {
                "tier": "basic",
                "amount": TIER_PRICES["basic"],
                "currency": "KES",
                "duration_days": 30,
            },
            {
                "tier": "pro",
                "amount": TIER_PRICES["pro"],
                "currency": "KES",
                "duration_days": 30,
            },
        ]
    }


@router.post("/stk-push", response_model=STKPushResponse)
async def initiate_payment(
    body: STKPushRequest,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
):
    tier = SubscriptionTierInfo(body.tier.value)
    amount = TIER_PRICES[tier.value]
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
            SubscriptionService(db).activate(txn.user_id, txn.tier.value)

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

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user
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

@router.post("/stk-push", response_model=STKPushResponse)
async def initiate_payment(
    body: STKPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tier = SubscriptionTierInfo(body.tier.value)
    amount = TIER_PRICES[tier.value]
    try:
        result = await mpesa.initiate_stk_push(
            phone=current_user.phone_number,
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
        phone_number=current_user.phone_number,
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
            return {"ResultCode": 0, "ResultDesc": "Accepted"}  # idempotency guard

        txn.raw_callback = payload
        txn.mpesa_response_code = str(result_code)
        txn.mpesa_response_description = stk_callback.get("ResultDesc")

        if result_code == 0:
            # Extract M-Pesa receipt from metadata
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            meta  = {i["Name"]: i.get("Value") for i in items}

            txn.status = TransactionStatus.COMPLETED
            txn.mpesa_receipt_number = meta.get("MpesaReceiptNumber")
            txn.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Upgrade subscription
            SubscriptionService(db).activate(txn.user_id, txn.tier.value)

            # Fire-and-forget email (Celery)
            from app.tasks.email_tasks import send_payment_confirmation
            send_payment_confirmation.delay(txn.user_id, txn.mpesa_receipt_number, str(txn.amount))

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

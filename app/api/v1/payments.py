from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.services.mpesa_service import MpesaService
from app.services.subscription_service import SubscriptionService
from app.schemas.payments import STKPushRequest, STKPushResponse
from app.core.audit import log_action  # you likely have this already
import logging

router = APIRouter(prefix="/payments", tags=["Payments"])
mpesa  = MpesaService()

TIER_PRICES = {"basic": 500, "pro": 1200}   # KES

@router.post("/stk-push", response_model=STKPushResponse)
async def initiate_payment(
    body: STKPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    amount = TIER_PRICES[body.tier]
    try:
        result = await mpesa.initiate_stk_push(
            phone=current_user.phone_number,
            amount=amount,
            account_ref="SAFARIDESK-SUB",
            description=f"{body.tier.upper()} subscription",
        )
    except Exception as e:
        logging.error(f"STK Push failed: {e}")
        raise HTTPException(502, "M-Pesa request failed. Try again.")

    if result.get("ResponseCode") != "0":
        raise HTTPException(400, result.get("ResponseDescription", "STK Push rejected"))

    # Persist pending transaction
    txn = Transaction(
        user_id=current_user.id,
        checkout_request_id=result["CheckoutRequestID"],
        merchant_request_id=result["MerchantRequestID"],
        amount=amount,
        tier=body.tier,
        status="PENDING",
        phone_number=current_user.phone_number,
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
            checkout_request_id=checkout_id
        ).first()

        if not txn:
            return {"ResultCode": 0, "ResultDesc": "Accepted"}  # unknown, ignore

        if txn.status != "PENDING":
            return {"ResultCode": 0, "ResultDesc": "Accepted"}  # idempotency guard

        if result_code == 0:
            # Extract M-Pesa receipt from metadata
            items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
            meta  = {i["Name"]: i.get("Value") for i in items}

            txn.status      = "COMPLETED"
            txn.mpesa_receipt = meta.get("MpesaReceiptNumber")
            db.commit()

            # Upgrade subscription
            SubscriptionService(db).activate(txn.user_id, txn.tier)

            # Fire-and-forget email (Celery)
            from app.tasks.email_tasks import send_payment_confirmation
            send_payment_confirmation.delay(txn.user_id, txn.mpesa_receipt, txn.amount)

        else:
            txn.status       = "FAILED"
            txn.failure_reason = stk_callback["ResultDesc"]
            db.commit()

    except Exception as e:
        logging.error(f"Callback processing error: {e}")
        # Still return 200 — never let Safaricom see a 5xx

    return {"ResultCode": 0, "ResultDesc": "Accepted"}
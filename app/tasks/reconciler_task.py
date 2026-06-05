import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.transaction import Transaction, TransactionStatus
from app.services.mpesa_service import MpesaService
from app.services.subscription_service import SubscriptionService
from app.tasks.email_tasks import send_payment_confirmation, send_payment_failed
from app.tasks.sms_tasks import send_payment_confirmation_sms

logger = logging.getLogger(__name__)

# How long to wait before reconciling a PENDING transaction
PENDING_TIMEOUT_MINUTES = 5

# How many times to retry before giving up
MAX_RECONCILE_ATTEMPTS = 3


@celery_app.task(
    name="app.tasks.reconciler_task.reconcile_pending_transactions",
    bind=True,
    max_retries=3,
)
def reconcile_pending_transactions(self):
    """
    Runs every 5 minutes via Celery Beat.
    Finds all PENDING transactions older than 5 minutes
    and queries Daraja for their real status.

    Handles 3 outcomes:
      ResultCode 0        → COMPLETED → activate subscription
      ResultCode 1032     → CANCELLED (user cancelled on phone)
      Any other code      → FAILED
      Daraja unreachable  → leave PENDING, retry next cycle
    """
    db = SessionLocal()
    mpesa = MpesaService()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=PENDING_TIMEOUT_MINUTES)

        pending_txns = db.query(Transaction).filter(
            Transaction.status == TransactionStatus.PENDING,
            Transaction.initiated_at <= cutoff,
        ).all()

        if not pending_txns:
            logger.info("Reconciler: no pending transactions to process.")
            return

        logger.info(f"Reconciler: found {len(pending_txns)} pending transaction(s) to reconcile.")

        for txn in pending_txns:
            try:
                _reconcile_single(txn, db, mpesa)
            except Exception as e:
                logger.error(f"Reconciler: failed to reconcile txn {txn.id} — {e}")
                continue

    except Exception as exc:
        logger.exception("Reconciler task crashed.")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


def _reconcile_single(txn, db, mpesa):
    """Reconcile a single pending transaction against Daraja."""
    if txn.status != TransactionStatus.PENDING:
        logger.info(f"Reconciler: txn {txn.id} already {txn.status}; skipping.")
        return

    logger.info(f"Reconciler: querying status for txn {txn.id} | {txn.mpesa_request_id}")

    try:
        result = asyncio.run(mpesa.query_stk_status(txn.mpesa_request_id))
    except Exception as e:
        logger.warning(f"Reconciler: Daraja query failed for txn {txn.id} — {e}. Will retry next cycle.")
        return

    result_code = str(result.get("ResultCode", ""))
    result_desc = result.get("ResultDesc", "Unknown")

    txn.raw_callback = result
    txn.mpesa_response_code = result_code
    txn.mpesa_response_description = result_desc

    logger.info(f"Reconciler: txn {txn.id} → ResultCode={result_code} | {result_desc}")

    if result_code == "0":
        # Payment confirmed — activate subscription
        txn.status       = TransactionStatus.COMPLETED
        txn.completed_at = datetime.now(timezone.utc)
        txn.failure_reason = None
        txn.mpesa_receipt_number = (
            result.get("MpesaReceiptNumber")
            or result.get("ReceiptNumber")
            or txn.mpesa_receipt_number
        )
        db.commit()

        SubscriptionService(db).activate(txn.user_id, txn.tier.value)

        # Send confirmation email
        send_payment_confirmation.delay(
            txn.user_id,
            txn.mpesa_receipt_number,
            str(txn.amount),
        )
        send_payment_confirmation_sms.delay(txn.user_id, str(txn.amount))
        logger.info(f"Reconciler: txn {txn.id} COMPLETED — subscription activated for user {txn.user_id}")

    elif result_code == "1032":
        # User cancelled on phone
        txn.status         = TransactionStatus.CANCELLED
        txn.failure_reason = "Request cancelled by user"
        db.commit()

        send_payment_failed.delay(txn.user_id, str(txn.amount), "Payment was cancelled.")
        logger.info(f"Reconciler: txn {txn.id} CANCELLED by user.")

    elif result_code in ("1037", "1001"):
        # 1037 = timeout, 1001 = insufficient funds
        reason_map = {
            "1037": "Payment timed out. Please try again.",
            "1001": "Insufficient M-Pesa balance.",
        }
        txn.status         = TransactionStatus.FAILED
        txn.failure_reason = reason_map.get(result_code, result_desc)
        db.commit()

        send_payment_failed.delay(txn.user_id, str(txn.amount), txn.failure_reason)
        logger.info(f"Reconciler: txn {txn.id} FAILED — {txn.failure_reason}")

    else:
        # Unknown result — mark failed to avoid stuck transactions
        txn.status         = TransactionStatus.FAILED
        txn.failure_reason = result_desc
        db.commit()

        send_payment_failed.delay(txn.user_id, str(txn.amount), result_desc)
        logger.warning(f"Reconciler: txn {txn.id} unknown ResultCode={result_code} — marked FAILED.")

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class TransactionStatus(str, enum.Enum):
    INITIATED = "initiated"   # STK push sent to phone
    PENDING = "pending"       # User has not responded yet
    COMPLETED = "completed"   # Payment confirmed by M-Pesa callback
    FAILED = "failed"         # Payment failed or cancelled
    CANCELLED = "cancelled"   # User cancelled on phone
    REVERSED = "reversed"     # Refund processed

class TransactionType(str, enum.Enum):
    SUBSCRIPTION_PAYMENT = "subscription_payment"
    REFUND = "refund"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    # M-Pesa specific fields
    mpesa_request_id = Column(String, unique=True, index=True)  # CheckoutRequestID
    mpesa_receipt_number = Column(String, unique=True, nullable=True, index=True)
    # ^^^ This is your IDEMPOTENCY KEY — unique per completed transaction

    phone_number = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="KES")

    transaction_type = Column(Enum(TransactionType))
    status = Column(Enum(TransactionStatus), default=TransactionStatus.INITIATED)

    # M-Pesa response details
    mpesa_response_code = Column(String, nullable=True)
    mpesa_response_description = Column(Text, nullable=True)

    # Raw M-Pesa callback stored as JSON — always keep the raw response
    raw_callback = Column(JSONB, nullable=True)

    # Timestamps
    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Transaction {self.mpesa_receipt_number} | {self.status}>"
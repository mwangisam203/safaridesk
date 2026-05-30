from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    GRACE_PERIOD = "grace_period"  # 3 days after expiry before losing access
    PENDING = "pending"            # Payment initiated but not confirmed yet

class SubscriptionTierInfo(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    tier = Column(Enum(SubscriptionTierInfo), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING)

    # Pricing at time of subscription — store it, prices may change later
    amount_paid = Column(Numeric(10, 2), nullable=True)
    currency = Column(String, default="KES")

    # Lifecycle dates
    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Auto renewal
    auto_renew = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    # user = relationship("User", back_populates="subscriptions")
    # transactions = relationship("Transaction", back_populates="subscription")
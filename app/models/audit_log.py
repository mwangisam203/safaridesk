from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # What happened
    action = Column(String, nullable=False, index=True)
    # Examples: "payment_initiated", "subscription_upgraded",
    #           "subscription_expired", "refund_processed", "login_failed"

    # What was affected
    entity_type = Column(String, nullable=True)   # "transaction", "subscription"
    entity_id = Column(String, nullable=True)     # The ID of the affected record

    # Full context of the action
    log_metadata = Column(JSONB, nullable=True)

    # Request context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Always recorded, never updated, never deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # No update methods — this table is append only
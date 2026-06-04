from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class AnonymousRead(Base):
    __tablename__ = "anonymous_reads"

    id             = Column(Integer, primary_key=True, index=True)
    fingerprint_id = Column(String, nullable=False, index=True)  # cookie UUID
    ip_address     = Column(String, nullable=False)
    article_id     = Column(Integer, ForeignKey("articles.id"), nullable=False)
    read_at        = Column(DateTime(timezone=True), server_default=func.now())


class AnonymousEmail(Base):
    __tablename__ = "anonymous_emails"

    id             = Column(Integer, primary_key=True, index=True)
    email          = Column(String, nullable=False, index=True)
    fingerprint_id = Column(String, nullable=False, index=True)
    captured_at    = Column(DateTime(timezone=True), server_default=func.now())

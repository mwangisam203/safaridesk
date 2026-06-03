from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class ArticleTier(str, enum.Enum):
    BASIC = "basic"
    PRO   = "pro"


class Article(Base):
    __tablename__ = "articles"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(255), nullable=False)
    slug         = Column(String(255), unique=True, index=True, nullable=False)
    summary      = Column(String(500), nullable=True)   # short preview for FREE users
    body         = Column(Text, nullable=False)
    tier         = Column(Enum(ArticleTier), nullable=False, default=ArticleTier.BASIC)
    author       = Column(String(100), nullable=False, default="SafariDesk Team")
    is_published = Column(Boolean, default=False)       # draft until True
    view_count   = Column(Integer, default=0)

    # Timestamps
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Article {self.slug} | {self.tier} | published={self.is_published}>"

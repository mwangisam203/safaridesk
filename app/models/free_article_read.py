from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class FreeArticleRead(Base):
    __tablename__ = "free_article_reads"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    read_at    = Column(DateTime(timezone=True), server_default=func.now())

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.article import ArticleTier


# ── Admin: create article ─────────────────────────────────────────────────────
class ArticleCreate(BaseModel):
    title:        str         = Field(..., min_length=5, max_length=255)
    slug:         str         = Field(..., min_length=3, max_length=255)
    summary:      Optional[str] = Field(None, max_length=500)
    body:         str         = Field(..., min_length=10)
    tier:         ArticleTier = ArticleTier.BASIC
    author:       str         = "SafariDesk Team"
    is_published: bool        = False


# ── Admin: update article ─────────────────────────────────────────────────────
class ArticleUpdate(BaseModel):
    title:        Optional[str]         = None
    summary:      Optional[str]         = None
    body:         Optional[str]         = None
    tier:         Optional[ArticleTier] = None
    author:       Optional[str]         = None
    is_published: Optional[bool]        = None


# ── Public: article list item (no body — saves bandwidth) ────────────────────
class ArticleListItem(BaseModel):
    model_config = {"from_attributes": True}

    id:           int
    title:        str
    slug:         str
    summary:      Optional[str]
    tier:         ArticleTier
    author:       str
    view_count:   int
    published_at: Optional[datetime]


# ── Public: full article ──────────────────────────────────────────────────────
class ArticleDetail(ArticleListItem):
    model_config = {"from_attributes": True}

    body:       str
    created_at: datetime
    updated_at: Optional[datetime]

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.article import ArticleTier


# ── Admin: create article ─────────────────────────────────────────────────────
class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    slug: str = Field(
        ...,
        min_length=3,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    summary: Optional[str] = Field(None, max_length=500)
    body: str = Field(..., min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    cover_image_alt: Optional[str] = Field(None, max_length=255)
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = Field(None, max_length=500)
    is_featured: bool = False
    tier: ArticleTier = ArticleTier.BASIC
    author: str = Field("SafariDesk Team", min_length=2, max_length=100)
    is_published: bool = False


# ── Admin: update article ─────────────────────────────────────────────────────
class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    slug: Optional[str] = Field(
        None,
        min_length=3,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    summary: Optional[str] = Field(None, max_length=500)
    body: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    cover_image_alt: Optional[str] = Field(None, max_length=255)
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = Field(None, max_length=500)
    is_featured: Optional[bool] = None
    tier: Optional[ArticleTier] = None
    author: Optional[str] = Field(None, min_length=2, max_length=100)
    is_published: Optional[bool] = None


# ── Public: article list item (no body — saves bandwidth) ────────────────────
class ArticleListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    title: str
    slug: str
    summary: Optional[str]
    category: Optional[str]
    cover_image_url: Optional[str]
    cover_image_alt: Optional[str]
    is_featured: bool
    tier: ArticleTier
    author: str
    view_count: int
    published_at: Optional[datetime]


# ── Public: full article ──────────────────────────────────────────────────────
class ArticleDetail(ArticleListItem):
    model_config = {"from_attributes": True}

    body: str
    seo_title: Optional[str]
    seo_description: Optional[str]
    is_published: bool
    created_at: datetime
    updated_at: Optional[datetime]

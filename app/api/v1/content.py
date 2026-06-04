from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_active_subscription
from app.models.article import Article, ArticleTier
from app.models.free_article_read import FreeArticleRead
from app.models.user import User, SubscriptionTier
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleListItem, ArticleDetail

router = APIRouter(prefix="/content", tags=["Content"])

FREE_ARTICLE_LIMIT  = 10
FREE_RESET_DAYS     = 10


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_article_or_404(slug: str, db: Session) -> Article:
    article = db.query(Article).filter_by(slug=slug, is_published=True).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article


def get_free_reads_count(user_id: int, db: Session) -> int:
    """Count how many free articles this user has read in the last 10 days."""
    since = datetime.now(timezone.utc) - timedelta(days=FREE_RESET_DAYS)
    return db.query(FreeArticleRead).filter(
        FreeArticleRead.user_id == user_id,
        FreeArticleRead.read_at >= since,
    ).count()


def already_read(user_id: int, article_id: int, db: Session) -> bool:
    """Check if user already read this specific article (don't double count)."""
    since = datetime.now(timezone.utc) - timedelta(days=FREE_RESET_DAYS)
    return db.query(FreeArticleRead).filter(
        FreeArticleRead.user_id == user_id,
        FreeArticleRead.article_id == article_id,
        FreeArticleRead.read_at >= since,
    ).first() is not None


# ── List articles ─────────────────────────────────────────────────────────────
@router.get("/articles", response_model=list[ArticleListItem])
def list_articles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Everyone can see the article list (title + summary).
    FREE users see BASIC articles only.
    Subscribers see articles matching their tier.
    """
    if current_user.subscription_tier == SubscriptionTier.PRO:
        articles = db.query(Article).filter_by(
            is_published=True
        ).order_by(Article.published_at.desc()).all()
    else:
        # FREE and BASIC both see basic list
        articles = db.query(Article).filter_by(
            is_published=True, tier=ArticleTier.BASIC
        ).order_by(Article.published_at.desc()).all()

    return articles


# ── Read one article ──────────────────────────────────────────────────────────
@router.get("/articles/{slug}", response_model=ArticleDetail)
def get_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = get_article_or_404(slug, db)

    # PRO articles — subscribers only, no free access
    if article.tier == ArticleTier.PRO:
        if current_user.subscription_tier != SubscriptionTier.PRO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This article requires a PRO subscription.",
            )

    # BASIC articles — subscribers get in freely
    if current_user.subscription_tier in (SubscriptionTier.BASIC, SubscriptionTier.PRO):
        article.view_count += 1
        db.commit()
        db.refresh(article)
        return article

    # FREE user hitting a BASIC article — apply 10-article limit
    if not already_read(current_user.id, article.id, db):
        reads = get_free_reads_count(current_user.id, db)

        if reads >= FREE_ARTICLE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"You have used all {FREE_ARTICLE_LIMIT} free articles. "
                    f"Your access resets every {FREE_RESET_DAYS} days, or subscribe "
                    f"for unlimited access at /api/v1/payments/stk-push."
                ),
            )

        # Record the free read
        db.add(FreeArticleRead(user_id=current_user.id, article_id=article.id))

    article.view_count += 1
    db.commit()
    db.refresh(article)
    return article


# ── Admin: create article ─────────────────────────────────────────────────────
@router.post("/admin/articles", response_model=ArticleDetail, status_code=201)
def create_article(
    body: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admins only.")

    if db.query(Article).filter_by(slug=body.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists.")

    article = Article(**body.model_dump())
    if body.is_published:
        article.published_at = datetime.now(timezone.utc)

    db.add(article)
    db.commit()
    db.refresh(article)
    return article


# ── Admin: update article ─────────────────────────────────────────────────────
@router.patch("/admin/articles/{slug}", response_model=ArticleDetail)
def update_article(
    slug: str,
    body: ArticleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admins only.")

    article = db.query(Article).filter_by(slug=slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(article, field, value)

    if body.is_published and not article.published_at:
        article.published_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(article)
    return article


# ── Admin: delete article ─────────────────────────────────────────────────────
@router.delete("/admin/articles/{slug}", status_code=204)
def delete_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admins only.")

    article = db.query(Article).filter_by(slug=slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    db.delete(article)
    db.commit()


# ── Search articles ───────────────────────────────────────────────────────────
@router.get("/articles/search", response_model=list[ArticleListItem])
def search_articles(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search articles by keyword in title, summary or body.
    FREE users see BASIC results only.
    """
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters.")

    keyword = f"%{q.lower()}%"

    query = db.query(Article).filter(
        Article.is_published == True,
        (
            Article.title.ilike(keyword) |
            Article.summary.ilike(keyword) |
            Article.body.ilike(keyword)
        )
    )

    # FREE users only see BASIC articles
    if current_user.subscription_tier == SubscriptionTier.FREE:
        query = query.filter(Article.tier == ArticleTier.BASIC)

    # BASIC users only see BASIC articles
    elif current_user.subscription_tier == SubscriptionTier.BASIC:
        query = query.filter(Article.tier == ArticleTier.BASIC)

    # PRO sees everything
    results = query.order_by(Article.published_at.desc()).all()

    if not results:
        raise HTTPException(status_code=404, detail=f"No articles found for '{q}'.")

    return results

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_active_subscription, require_pro_subscription
from app.models.article import Article, ArticleTier
from app.models.user import User
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticleListItem, ArticleDetail

router = APIRouter(prefix="/content", tags=["Content"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_article_or_404(slug: str, db: Session) -> Article:
    article = db.query(Article).filter_by(slug=slug, is_published=True).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article


# ── Public: list articles (subscribers only) ──────────────────────────────────
@router.get("/articles", response_model=list[ArticleListItem])
def list_articles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription),
):
    """Returns all published articles the user's tier can access."""
    if current_user.subscription_tier == "pro":
        # PRO sees everything
        articles = db.query(Article).filter_by(is_published=True).order_by(Article.published_at.desc()).all()
    else:
        # BASIC sees basic only
        articles = db.query(Article).filter_by(
            is_published=True, tier=ArticleTier.BASIC
        ).order_by(Article.published_at.desc()).all()
    return articles


# ── Public: read one article ──────────────────────────────────────────────────
@router.get("/articles/{slug}", response_model=ArticleDetail)
def get_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription),
):
    article = get_article_or_404(slug, db)

    # BASIC user trying to read a PRO article
    if article.tier == ArticleTier.PRO and current_user.subscription_tier != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This article requires a PRO subscription.",
        )

    # Increment view count
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

    # Set published_at when publishing for the first time
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

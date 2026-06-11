from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.article import Article, ArticleTier
from app.models.audit_log import AuditLog
from app.models.free_article_read import FreeArticleRead
from app.models.anonymous_read import AnonymousRead, AnonymousEmail
from app.models.user import User, SubscriptionTier
from app.schemas.article import (
    ArticleCreate,
    ArticleUpdate,
    ArticleListItem,
    ArticleDetail,
)

router = APIRouter(prefix="/content", tags=["Content"])

FREE_ARTICLE_LIMIT = 10
FREE_RESET_DAYS = 10
ANON_SOFT_WALL = 5  # articles before email prompt
ANON_HARD_WALL = 10  # articles before registration wall
FINGERPRINT_COOKIE = "sd_fid"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════


def get_or_create_fingerprint(request: Request, response: Response) -> str:
    """Get existing fingerprint cookie or create a new one."""
    fid = request.cookies.get(FINGERPRINT_COOKIE)
    if not fid:
        fid = str(uuid.uuid4())
        response.set_cookie(
            key=FINGERPRINT_COOKIE,
            value=fid,
            max_age=60 * 60 * 24 * 365,  # 1 year
            httponly=True,
            samesite="lax",
        )
    return fid


def get_anon_read_count(fingerprint_id: str, db: Session) -> int:
    """Count anonymous reads in last 10 days."""
    since = datetime.now(timezone.utc) - timedelta(days=FREE_RESET_DAYS)
    return (
        db.query(AnonymousRead)
        .filter(
            AnonymousRead.fingerprint_id == fingerprint_id,
            AnonymousRead.read_at >= since,
        )
        .count()
    )


def anon_already_read(fingerprint_id: str, article_id: int, db: Session) -> bool:
    """Check if anonymous user already read this article in current window."""
    since = datetime.now(timezone.utc) - timedelta(days=FREE_RESET_DAYS)
    return (
        db.query(AnonymousRead)
        .filter(
            AnonymousRead.fingerprint_id == fingerprint_id,
            AnonymousRead.article_id == article_id,
            AnonymousRead.read_at >= since,
        )
        .first()
        is not None
    )


def anon_has_submitted_email(fingerprint_id: str, db: Session) -> bool:
    """Check if anonymous user already submitted their email."""
    return (
        db.query(AnonymousEmail).filter_by(fingerprint_id=fingerprint_id).first()
        is not None
    )


def get_free_reads_count(user_id: int, db: Session) -> int:
    """Count free reads for registered FREE user in last 10 days."""
    since = datetime.now(timezone.utc) - timedelta(days=FREE_RESET_DAYS)
    return (
        db.query(FreeArticleRead)
        .filter(
            FreeArticleRead.user_id == user_id,
            FreeArticleRead.read_at >= since,
        )
        .count()
    )


def already_read(user_id: int, article_id: int, db: Session) -> bool:
    """Check if registered user already read this article in current window."""
    since = datetime.now(timezone.utc) - timedelta(days=FREE_RESET_DAYS)
    return (
        db.query(FreeArticleRead)
        .filter(
            FreeArticleRead.user_id == user_id,
            FreeArticleRead.article_id == article_id,
            FreeArticleRead.read_at >= since,
        )
        .first()
        is not None
    )


def get_article_or_404(slug: str, db: Session) -> Article:
    article = db.query(Article).filter_by(slug=slug, is_published=True).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article


def record_article_audit(
    db: Session,
    request: Request,
    current_user: User,
    action: str,
    article: Article,
    metadata: Optional[dict] = None,
) -> None:
    db.add(
        AuditLog(
            user_id=current_user.id,
            action=action,
            entity_type="article",
            entity_id=str(article.id) if article.id is not None else article.slug,
            log_metadata={"slug": article.slug, **(metadata or {})},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# Public — no auth required
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/articles", response_model=list[ArticleListItem])
def list_articles(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Everyone sees the article list — titles and summaries only.
    No auth required. PRO articles hidden from anonymous/free users.
    """
    token = request.headers.get("Authorization")

    if token:
        # Try to identify the user
        try:
            from app.core.dependencies import get_current_user
            from app.core.security import decode_token

            raw = token.replace("Bearer ", "")
            payload = decode_token(raw)
            user_id = int(payload.get("sub"))
            user = db.get(User, user_id)
            if user and user.subscription_tier == SubscriptionTier.PRO:
                return (
                    db.query(Article)
                    .filter_by(is_published=True)
                    .order_by(Article.published_at.desc())
                    .all()
                )
        except Exception:
            pass

    # Anonymous or FREE/BASIC — show BASIC articles only
    return (
        db.query(Article)
        .filter_by(is_published=True, tier=ArticleTier.BASIC)
        .order_by(Article.published_at.desc())
        .all()
    )


@router.get("/articles/search", response_model=list[ArticleListItem])
def search_articles(
    q: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Search articles by keyword. Works for everyone including anonymous users."""
    if len(q.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Search query must be at least 2 characters."
        )

    keyword = f"%{q.lower()}%"
    show_pro = False

    token = request.headers.get("Authorization")
    if token:
        try:
            from app.core.security import decode_token

            raw = token.replace("Bearer ", "")
            payload = decode_token(raw)
            user_id = int(payload.get("sub"))
            user = db.get(User, user_id)
            if user and user.subscription_tier == SubscriptionTier.PRO:
                show_pro = True
        except Exception:
            pass

    query = db.query(Article).filter(
        Article.is_published == True,
        (
            Article.title.ilike(keyword)
            | Article.summary.ilike(keyword)
            | Article.body.ilike(keyword)
        ),
    )

    if not show_pro:
        query = query.filter(Article.tier == ArticleTier.BASIC)

    results = query.order_by(Article.published_at.desc()).all()

    if not results:
        raise HTTPException(status_code=404, detail=f"No articles found for '{q}'.")

    return results


@router.get("/articles/{slug}", response_model=ArticleDetail)
def get_article(
    slug: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Read a full article.
    - Anonymous: 0-5 free, 6-10 after email, 11+ register
    - FREE registered: up to 10 per 10 days
    - BASIC: unlimited BASIC articles
    - PRO: unlimited everything
    """
    article = get_article_or_404(slug, db)
    token = request.headers.get("Authorization")
    user = None

    # Try to get logged in user
    if token:
        try:
            from app.core.security import decode_token

            raw = token.replace("Bearer ", "")
            payload = decode_token(raw)
            user_id = int(payload.get("sub"))
            user = db.get(User, user_id)
        except Exception:
            pass

    # ── Authenticated user ────────────────────────────────────────────────────
    if user:
        # PRO articles blocked for non-PRO
        if (
            article.tier == ArticleTier.PRO
            and user.subscription_tier != SubscriptionTier.PRO
        ):
            raise HTTPException(
                status_code=403,
                detail="This article requires a PRO subscription.",
            )

        # Subscribers — unlimited access
        if user.subscription_tier in (SubscriptionTier.BASIC, SubscriptionTier.PRO):
            article.view_count += 1
            db.commit()
            db.refresh(article)
            return article

        # FREE registered user — 10 article limit
        if not already_read(user.id, article.id, db):
            reads = get_free_reads_count(user.id, db)
            if reads >= FREE_ARTICLE_LIMIT:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "action": "subscribe",
                        "message": f"You have used all {FREE_ARTICLE_LIMIT} free articles. Subscribe to continue.",
                        "subscribe_url": "/api/v1/payments/stk-push",
                        "resets_in_days": FREE_RESET_DAYS,
                    },
                )
            db.add(FreeArticleRead(user_id=user.id, article_id=article.id))

        article.view_count += 1
        db.commit()
        db.refresh(article)
        return article

    # ── Anonymous user ────────────────────────────────────────────────────────
    # PRO articles always blocked for anonymous
    if article.tier == ArticleTier.PRO:
        raise HTTPException(
            status_code=403,
            detail={
                "action": "register",
                "message": "Create an account and subscribe to access PRO content.",
            },
        )

    fid = get_or_create_fingerprint(request, response)

    if not anon_already_read(fid, article.id, db):
        reads = get_anon_read_count(fid, db)

        # Hard wall — must register
        if reads >= ANON_HARD_WALL:
            raise HTTPException(
                status_code=403,
                detail={
                    "action": "register",
                    "message": "You've read 10 free articles. Create a free account to keep reading.",
                    "register_url": "/api/v1/auth/register",
                    "resets_in_days": FREE_RESET_DAYS,
                },
            )

        # Soft wall — submit email to unlock articles 6-10
        if reads >= ANON_SOFT_WALL and not anon_has_submitted_email(fid, db):
            raise HTTPException(
                status_code=403,
                detail={
                    "action": "soft_wall",
                    "message": "Enter your email to keep reading — it's free.",
                    "submit_url": "/api/v1/content/email-capture",
                    "resets_in_days": FREE_RESET_DAYS,
                },
            )

        db.add(
            AnonymousRead(
                fingerprint_id=fid,
                ip_address=request.client.host,
                article_id=article.id,
            )
        )

    article.view_count += 1
    db.commit()
    db.refresh(article)
    return article


# ── Email capture (soft wall) ─────────────────────────────────────────────────
@router.post("/email-capture", status_code=200)
def capture_email(
    payload: dict,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Anonymous user submits email to unlock articles 6-10."""
    email = payload.get("email", "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required.")

    fid = get_or_create_fingerprint(request, response)

    # Don't save duplicates
    if not anon_has_submitted_email(fid, db):
        db.add(AnonymousEmail(email=email, fingerprint_id=fid))
        db.commit()

    return {"message": "Thank you! You can now continue reading."}


# ══════════════════════════════════════════════════════════════════════════════
# Admin endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/admin/articles", response_model=list[ArticleDetail])
def list_admin_articles(
    is_published: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(Article)
    if is_published is not None:
        query = query.filter(Article.is_published == is_published)
    return query.order_by(Article.updated_at.desc(), Article.created_at.desc()).all()


@router.get("/admin/articles/{slug}", response_model=ArticleDetail)
def get_admin_article(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    article = db.query(Article).filter_by(slug=slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")
    return article


@router.post("/admin/articles", response_model=ArticleDetail, status_code=201)
def create_article(
    body: ArticleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if db.query(Article).filter_by(slug=body.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists.")

    article = Article(**body.model_dump())
    if body.is_published:
        article.published_at = datetime.now(timezone.utc)

    db.add(article)
    db.flush()
    record_article_audit(
        db,
        request,
        current_user,
        "article_created",
        article,
        {"is_published": body.is_published},
    )
    db.commit()
    db.refresh(article)
    return article


@router.patch("/admin/articles/{slug}", response_model=ArticleDetail)
def update_article(
    slug: str,
    body: ArticleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    article = db.query(Article).filter_by(slug=slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    updates = body.model_dump(exclude_unset=True)
    new_slug = updates.get("slug")
    if new_slug and new_slug != slug:
        existing = db.query(Article).filter_by(slug=new_slug).first()
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists.")

    was_published = article.is_published
    for field, value in updates.items():
        setattr(article, field, value)

    if body.is_published and not article.published_at:
        article.published_at = datetime.now(timezone.utc)

    action = "article_updated"
    if body.is_published is True and not was_published:
        action = "article_published"
    elif body.is_published is False and was_published:
        action = "article_unpublished"
    record_article_audit(
        db,
        request,
        current_user,
        action,
        article,
        {"updated_fields": sorted(updates)},
    )
    db.commit()
    db.refresh(article)
    return article


@router.delete("/admin/articles/{slug}", status_code=204)
def delete_article(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    article = db.query(Article).filter_by(slug=slug).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found.")

    record_article_audit(
        db,
        request,
        current_user,
        "article_deleted",
        article,
        {"title": article.title},
    )
    db.delete(article)
    db.commit()

from datetime import datetime, timezone

from app.content.article_catalog import ARTICLES
from app.db.session import SessionLocal
from app.models.article import Article


def sync_articles() -> tuple[int, int]:
    created = 0
    updated = 0
    db = SessionLocal()

    try:
        for content in ARTICLES:
            article = db.query(Article).filter_by(slug=content["slug"]).first()
            if article is None:
                article = Article(
                    **content,
                    is_published=True,
                    published_at=datetime.now(timezone.utc),
                )
                db.add(article)
                created += 1
                continue

            for field in ("title", "summary", "body", "tier", "author"):
                setattr(article, field, content[field])
            updated += 1

        db.commit()
        return created, updated
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    created_count, updated_count = sync_articles()
    print(f"Article catalog synced: {created_count} created, {updated_count} updated.")

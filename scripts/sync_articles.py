from datetime import datetime, timezone

from app.content.article_catalog import ARTICLES
from app.db.session import SessionLocal
from app.models.article import Article


ARTICLE_METADATA = {
    "deploying-fastapi-to-linux-vps": ("DevOps", "deploying-fastapi-linux-vps.webp"),
    "linux-command-line-for-developers": ("DevOps", "linux-command-line.webp"),
    "writing-tests-fastapi-pytest": ("Testing", "fastapi-pytest.webp"),
    "python-virtual-environments-dependency-management": (
        "Python",
        "python-environments.webp",
    ),
    "git-github-for-backend-developers": ("Tooling", "git-collaboration.webp"),
    "alembic-database-migrations-in-practice": ("Database", "alembic-migrations.webp"),
    "mpesa-daraja-api-integration-guide": ("Payments", "mpesa-daraja.webp"),
    "celery-redis-background-tasks-explained": ("Background Jobs", "celery-redis.webp"),
    "introduction-to-docker-for-developers": ("DevOps", "docker-introduction.webp"),
    "understanding-jwt-authentication": ("Security", "jwt-authentication.webp"),
    "postgresql-for-backend-developers": ("Database", "postgresql-backend.webp"),
    "how-to-build-rest-api-fastapi": ("APIs", "rest-api-fastapi.webp"),
    "how-to-build-a-fastapi-backend": ("APIs", "fastapi-backend.webp"),
}


def article_values(content: dict) -> dict:
    category, cover_filename = ARTICLE_METADATA[content["slug"]]
    return {
        **content,
        "category": category,
        "cover_image_url": f"/covers/{cover_filename}",
        "cover_image_alt": f"Editorial illustration for {content['title']}",
        "seo_title": f"{content['title']} | SafariDesk",
        "seo_description": content["summary"],
        "is_featured": content["slug"] == "deploying-fastapi-to-linux-vps",
    }


def sync_articles() -> tuple[int, int]:
    created = 0
    updated = 0
    db = SessionLocal()

    try:
        for catalog_entry in ARTICLES:
            content = article_values(catalog_entry)
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

            for field in (
                "title",
                "summary",
                "body",
                "tier",
                "author",
                "category",
                "cover_image_url",
                "cover_image_alt",
                "seo_title",
                "seo_description",
                "is_featured",
            ):
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

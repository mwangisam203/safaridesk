from app.content.article_catalog import ARTICLES, ARTICLES_BY_SLUG
from scripts.sync_articles import ARTICLE_METADATA, article_values


def test_article_catalog_has_unique_slugs():
    slugs = [article["slug"] for article in ARTICLES]

    assert len(ARTICLES) == 13
    assert len(slugs) == len(set(slugs))
    assert set(slugs) == set(ARTICLES_BY_SLUG)


def test_article_catalog_contains_substantive_field_guides():
    for article in ARTICLES:
        assert len(article["summary"]) <= 500
        assert len(article["body"].split()) >= 250
        assert article["body"].count("## ") >= 3


def test_every_catalog_article_has_editor_metadata():
    assert set(ARTICLE_METADATA) == set(ARTICLES_BY_SLUG)

    values = [article_values(article) for article in ARTICLES]

    assert sum(article["is_featured"] for article in values) == 1
    assert all(article["cover_image_url"].startswith("/covers/") for article in values)
    assert all(article["seo_description"] == article["summary"] for article in values)

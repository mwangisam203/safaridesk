from app.content.article_catalog import ARTICLES, ARTICLES_BY_SLUG


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

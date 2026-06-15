from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.api.v1 import content
from app.core.config import settings
from app.core import dependencies
from app.services import image_storage
from main import app


def make_image(
    image_format="PNG",
    size=(2400, 1600),
    color=(34, 139, 94),
):
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format=image_format)
    return output.getvalue()


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def test_local_article_image_is_resized_and_converted_to_webp(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(settings, "IMAGE_STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "IMAGE_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "IMAGE_MAX_WIDTH", 1200)
    monkeypatch.setattr(settings, "IMAGE_MAX_HEIGHT", 800)

    stored = image_storage.store_article_image(
        make_image(),
        "image/png",
        "GraphQL architecture.png",
    )

    assert stored.url.startswith("/uploads/articles/graphql-architecture-")
    assert stored.url.endswith(".webp")
    assert (stored.width, stored.height) == (1200, 800)

    saved_path = tmp_path / stored.url.removeprefix("/uploads/")
    assert saved_path.exists()
    with Image.open(saved_path) as saved:
        assert saved.format == "WEBP"
        assert saved.size == (1200, 800)


def test_article_image_rejects_unsupported_content_type():
    with pytest.raises(image_storage.ImageUploadError, match="JPEG, PNG, or WebP"):
        image_storage.store_article_image(
            make_image(),
            "image/gif",
            "cover.gif",
        )


def test_article_image_rejects_file_disguised_as_supported_image():
    with pytest.raises(image_storage.ImageUploadError, match="not a valid image"):
        image_storage.store_article_image(
            b"this is not a real png",
            "image/png",
            "cover.png",
        )


def test_s3_article_image_uses_public_base_url(monkeypatch):
    calls = []

    class FakeS3:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(settings, "IMAGE_STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "safaridesk-assets")
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "https://cdn.safaridesk.com")
    monkeypatch.setattr(image_storage.boto3, "client", lambda *args, **kwargs: FakeS3())

    stored = image_storage.store_article_image(
        make_image(size=(800, 500)),
        "image/png",
        "payments.png",
    )

    assert stored.url.startswith("https://cdn.safaridesk.com/articles/payments-")
    assert calls[0]["Bucket"] == "safaridesk-assets"
    assert calls[0]["ContentType"] == "image/webp"
    assert calls[0]["CacheControl"] == "public, max-age=31536000, immutable"


def test_article_image_upload_requires_admin_authentication():
    response = TestClient(app).post(
        "/api/v1/content/admin/article-images",
        files={"image": ("cover.png", make_image(size=(300, 200)), "image/png")},
    )

    assert response.status_code == 401


def test_admin_can_upload_article_image(monkeypatch):
    stored = image_storage.StoredImage(
        url="/uploads/articles/cover.webp",
        width=1200,
        height=750,
        size_bytes=42_000,
    )
    app.dependency_overrides[dependencies.require_admin] = lambda: object()
    monkeypatch.setattr(content, "store_article_image", lambda *args: stored)

    response = TestClient(app).post(
        "/api/v1/content/admin/article-images",
        files={"image": ("cover.png", make_image(size=(300, 200)), "image/png")},
    )

    assert response.status_code == 201
    assert response.json() == {
        "url": "/uploads/articles/cover.webp",
        "content_type": "image/webp",
        "width": 1200,
        "height": 750,
        "size_bytes": 42_000,
    }

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import uuid

import boto3
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ImageUploadError(ValueError):
    pass


@dataclass(frozen=True)
class StoredImage:
    url: str
    width: int
    height: int
    size_bytes: int
    content_type: str = "image/webp"


def store_article_image(
    data: bytes,
    content_type: str | None,
    original_filename: str | None,
) -> StoredImage:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ImageUploadError("Upload a JPEG, PNG, or WebP image.")

    max_bytes = settings.IMAGE_UPLOAD_MAX_MB * 1024 * 1024
    if not data:
        raise ImageUploadError("The uploaded image is empty.")
    if len(data) > max_bytes:
        raise ImageUploadError(
            f"Image must be {settings.IMAGE_UPLOAD_MAX_MB} MB or smaller."
        )

    output, width, height = _convert_to_webp(data)
    key = _object_key(original_filename)

    if settings.IMAGE_STORAGE_BACKEND.lower() == "s3":
        url = _store_in_s3(key, output)
    elif settings.IMAGE_STORAGE_BACKEND.lower() == "local":
        url = _store_locally(key, output)
    else:
        raise RuntimeError("IMAGE_STORAGE_BACKEND must be 'local' or 's3'.")

    return StoredImage(
        url=url,
        width=width,
        height=height,
        size_bytes=len(output),
    )


def _convert_to_webp(data: bytes) -> tuple[bytes, int, int]:
    try:
        with Image.open(BytesIO(data)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ImageUploadError("Upload a JPEG, PNG, or WebP image.")
            image = ImageOps.exif_transpose(source)
            image.thumbnail(
                (settings.IMAGE_MAX_WIDTH, settings.IMAGE_MAX_HEIGHT),
                Image.Resampling.LANCZOS,
            )

            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=84, method=6)
            return output.getvalue(), image.width, image.height
    except ImageUploadError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageUploadError("The uploaded file is not a valid image.") from exc


def _object_key(original_filename: str | None) -> str:
    stem = Path(original_filename or "article-cover").stem.lower()
    safe_stem = re.sub(r"[^a-z0-9]+", "-", stem).strip("-") or "article-cover"
    return f"articles/{safe_stem}-{uuid.uuid4().hex[:12]}.webp"


def _store_locally(key: str, data: bytes) -> str:
    upload_root = Path(settings.IMAGE_UPLOAD_DIR)
    destination = upload_root / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return f"/uploads/{key}"


def _store_in_s3(key: str, data: bytes) -> str:
    if not settings.S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME is required for S3 image storage.")

    client = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
    )
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType="image/webp",
        CacheControl="public, max-age=31536000, immutable",
    )

    if settings.S3_PUBLIC_BASE_URL:
        return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"

    region = settings.AWS_REGION
    return f"https://{settings.S3_BUCKET_NAME}.s3.{region}.amazonaws.com/{key}"

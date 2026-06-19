from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import Request


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()

    cloudflare_ip = request.headers.get("cf-connecting-ip")
    if cloudflare_ip:
        return cloudflare_ip.strip()

    return request.client.host if request.client else None


def email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return email.rsplit("@", 1)[1].lower()


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    payload = {
        "event": event,
        **{
            key: _jsonable(value)
            for key, value in fields.items()
            if value is not None
        },
    }
    logger.log(level, json.dumps(payload, sort_keys=True))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value

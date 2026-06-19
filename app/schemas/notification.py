from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    category: str
    title: str
    body: str
    action_url: str | None = None
    event_key: str | None = None
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int

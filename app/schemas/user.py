from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.user import SubscriptionTier


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    phone_number: str
    full_name: str
    subscription_tier: SubscriptionTier
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


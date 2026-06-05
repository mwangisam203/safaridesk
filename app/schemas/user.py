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


from typing import Optional
from app.models.subscription import SubscriptionStatus, SubscriptionTierInfo


class SubscriptionStatusResponse(BaseModel):
    tier:           SubscriptionTierInfo
    status:         Optional[SubscriptionStatus] = None
    started_at:     Optional[datetime] = None
    expires_at:     Optional[datetime] = None
    days_remaining: Optional[int] = None
    is_active:      bool = False
    message:        str  = ""

    model_config = {"from_attributes": True}

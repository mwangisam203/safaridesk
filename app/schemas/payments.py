from enum import Enum
import re

from pydantic import BaseModel, field_validator

class SubscriptionTierEnum(str, Enum):
    basic = "basic"
    pro   = "pro"

class STKPushRequest(BaseModel):
    tier: SubscriptionTierEnum
    phone_number: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_kenyan_phone(cls, v):
        if v is None:
            return v

        pattern = r'^(\+254|0)[17]\d{8}$'
        if not re.match(pattern, v):
            raise ValueError("Enter a valid Kenyan phone number")

        if v.startswith("0"):
            return "+254" + v[1:]
        return v

class STKPushResponse(BaseModel):
    checkout_request_id: str
    merchant_request_id: str
    message: str

class MpesaCallbackMetadataItem(BaseModel):
    Name: str
    Value: str | int | float | None = None

class MpesaCallbackBody(BaseModel):
    MerchantRequestID: str
    CheckoutRequestID: str
    ResultCode: int
    ResultDesc: str
    CallbackMetadata: dict | None = None

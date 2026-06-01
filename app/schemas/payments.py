from pydantic import BaseModel, Field
from enum import Enum

class SubscriptionTierEnum(str, Enum):
    basic = "basic"
    pro   = "pro"

class STKPushRequest(BaseModel):
    tier: SubscriptionTierEnum

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
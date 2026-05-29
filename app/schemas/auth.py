from pydantic import BaseModel, EmailStr, field_validator
import re

class RegisterRequest(BaseModel):
    email: EmailStr
    phone_number: str
    full_name: str
    password: str

    @field_validator("phone_number")
    @classmethod
    def validate_kenyan_phone(cls, v):
        # Accept +254XXXXXXXXX or 07XXXXXXXX or 01XXXXXXXX
        pattern = r'^(\+254|0)[17]\d{8}$'
        if not re.match(pattern, v):
            raise ValueError("Enter a valid Kenyan phone number")
        # Normalize to +254 format
        if v.startswith("0"):
            v = "+254" + v[1:]
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str

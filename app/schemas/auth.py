from pydantic import BaseModel, EmailStr, field_validator, model_validator
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
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return v

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str


class EmailRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("current_password", "new_password", "confirm_password")
    @classmethod
    def validate_password_size(cls, v):
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @model_validator(mode="after")
    def validate_confirmation(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation must match")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self


class VerificationResponse(BaseModel):
    message: str
    is_verified: bool

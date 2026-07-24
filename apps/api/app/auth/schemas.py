import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

PHONE_PATTERN = r"^\+[1-9]\d{7,14}$"


class PasswordRegisterRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if value.isalpha() or value.isdigit():
            raise ValueError("password must contain letters and numbers")
        return value


class PasswordLoginRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class OtpRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)


class OtpVerifyRequest(BaseModel):
    phone: str = Field(pattern=PHONE_PATTERN)
    code: str = Field(pattern=r"^\d{6}$")
    display_name: str = Field(default="Пользователь Lava", min_length=2, max_length=80)


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)


class UserResponse(BaseModel):
    id: uuid.UUID
    phone: str
    display_name: str
    role: str
    verification_level: int
    created_at: datetime
    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse


class OtpRequestResponse(BaseModel):
    status: str = "sent"
    dev_code: str | None = None


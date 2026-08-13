"""
Auth request / response schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "candidate"  # candidate | recruiter

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"candidate", "recruiter"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_name: str
    user_id: int


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

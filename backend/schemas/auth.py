"""Authentication schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email or identifier")
    password: str = Field(..., description="User password")


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=6, description="User password")
    full_name: str = Field(..., description="Full candidate name")


class UserPrincipal(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str] = None
    role: str = "candidate"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPrincipal

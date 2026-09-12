"""Pydantic schemas for operator users."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    DISPATCHER = "dispatcher"
    MANAGER = "manager"
    TRADER = "trader"


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    role: UserRole
    organization: str = Field(..., min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    organization: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
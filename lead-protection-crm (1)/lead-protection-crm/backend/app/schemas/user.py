from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.models.user import UserRole, EmployeeStatus
from app.core.phone import normalize_phone_e164

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)

class UserSignup(BaseModel):
    workspace_name: str = Field(..., min_length=2, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.USER
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v:
            return normalize_phone_e164(str(v))
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    status: Optional[EmployeeStatus] = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v:
            return normalize_phone_e164(str(v))
        return v

class UserRoleUpdate(BaseModel):
    role: UserRole

class UserStatusUpdate(BaseModel):
    status: EmployeeStatus

class UserOut(UserBase):
    id: str
    workspace_id: str
    role: UserRole
    status: EmployeeStatus
    is_active: bool
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

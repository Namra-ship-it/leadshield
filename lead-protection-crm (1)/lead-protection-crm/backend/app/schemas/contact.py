from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.schemas.company import CompanyOut
from app.core.phone import normalize_phone_e164

class ContactBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    company_id: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v:
            return normalize_phone_e164(str(v))
        return v

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    company_id: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v:
            return normalize_phone_e164(str(v))
        return v

class ContactOut(ContactBase):
    id: str
    workspace_id: str
    custom_fields: Dict[str, Any]
    company: Optional[CompanyOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

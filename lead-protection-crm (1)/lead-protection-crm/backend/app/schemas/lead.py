from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.lead import LeadStatus, LeadSource
from app.schemas.contact import ContactOut
from app.schemas.user import UserOut
from app.core.phone import normalize_phone_e164

class LeadBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None
    source: LeadSource = LeadSource.MANUAL
    custom_fields: Optional[Dict[str, Any]] = None

class LeadCreate(LeadBase):
    contact_id: Optional[str] = None
    owner_id: Optional[str] = None  # if not set, auto-routed via round-robin

class PublicLeadSubmit(BaseModel):
    workspace_slug: str = Field(..., min_length=1, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    inquiry: str = Field(..., min_length=1, max_length=1000)
    custom_fields: Optional[Dict[str, Any]] = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v:
            return normalize_phone_e164(str(v))
        return v

class LeadReassign(BaseModel):
    new_owner_id: str

class LeadOut(LeadBase):
    id: str
    workspace_id: str
    contact_id: Optional[str] = None
    owner_id: Optional[str] = None
    status: LeadStatus
    escalation_level: int
    assigned_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledgement_deadline: Optional[datetime] = None
    is_recovered: bool
    custom_fields: Dict[str, Any]
    contact: Optional[ContactOut] = None
    owner: Optional[UserOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

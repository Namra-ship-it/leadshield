from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.opportunity import PipelineStage
from app.schemas.contact import ContactOut
from app.schemas.company import CompanyOut
from app.schemas.user import UserOut

class OpportunityBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    value: float = Field(0.0, ge=0.0)
    currency: str = Field("INR", max_length=10)
    stage: PipelineStage = PipelineStage.NEW_LEAD
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class OpportunityCreate(OpportunityBase):
    pass

class OpportunityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = Field(None, max_length=10)
    stage: Optional[PipelineStage] = None
    contact_id: Optional[str] = None
    company_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class OpportunityStageUpdate(BaseModel):
    stage: PipelineStage

class OpportunityOut(OpportunityBase):
    id: str
    workspace_id: str
    stripe_payment_status: str
    stripe_session_id: Optional[str] = None
    custom_fields: Dict[str, Any]
    contact: Optional[ContactOut] = None
    company: Optional[CompanyOut] = None
    assigned_to: Optional[UserOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

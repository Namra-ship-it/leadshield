from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class CustomFieldCreate(BaseModel):
    entity_type: str = Field(..., pattern="^(contact|opportunity|company)$")
    label: str = Field(..., min_length=1, max_length=100)
    field_key: Optional[str] = Field(None, max_length=100)
    field_type: str = Field("text", pattern="^(text|number|select)$")
    options: Optional[List[str]] = Field(default_factory=list)

class CustomFieldOut(BaseModel):
    id: str
    workspace_id: str
    entity_type: str
    label: str
    field_key: str
    field_type: str
    options: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

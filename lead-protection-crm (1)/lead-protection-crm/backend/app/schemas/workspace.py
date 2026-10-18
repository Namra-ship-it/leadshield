from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)

class WorkspaceCreate(WorkspaceBase):
    slug: Optional[str] = Field(None, min_length=2, max_length=100)

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    settings: Optional[Dict[str, Any]] = None

class WorkspaceOut(WorkspaceBase):
    id: str
    slug: str
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return uuid.uuid4().hex

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    
    # Configurable lead engine timeouts and settings (configurable down to seconds!)
    settings = Column(JSON, default=lambda: {
        "acknowledgement_timeout_seconds": 300, # default 5 minutes, can be set to 20 for demo
        "escalation_backup_timeout_seconds": 300,
        "escalation_manager_timeout_seconds": 300,
        "max_open_leads_per_rep": 5,
        "auto_assign_enabled": True
    })

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    users = relationship("User", back_populates="workspace", cascade="all, delete-orphan")

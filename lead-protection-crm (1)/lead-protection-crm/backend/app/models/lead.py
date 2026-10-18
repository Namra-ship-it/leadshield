import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return uuid.uuid4().hex

class LeadStatus(str, enum.Enum):
    UNASSIGNED = "unassigned"
    PENDING_ACKNOWLEDGEMENT = "pending_acknowledgement"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RECOVERY_QUEUE = "recovery_queue"
    CLOSED = "closed"

class LeadSource(str, enum.Enum):
    WEB_FORM = "web_form"
    MANUAL = "manual"
    WHATSAPP = "whatsapp"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    notes = Column(String(1000), nullable=True)
    source = Column(String(32), default=LeadSource.MANUAL.value, nullable=False)
    status = Column(String(32), default=LeadStatus.UNASSIGNED.value, nullable=False, index=True)
    
    # Escalation tracking
    escalation_level = Column(Integer, default=0, nullable=False)
    assigned_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledgement_deadline = Column(DateTime, nullable=True, index=True)
    
    # Recovery queue flag
    is_recovered = Column(Boolean, default=False, nullable=False)

    custom_fields = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace")
    contact = relationship("Contact")
    owner = relationship("User", foreign_keys=[owner_id])

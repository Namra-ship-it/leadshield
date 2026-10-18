import uuid
import re
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, UniqueConstraint
from app.core.database import Base

def generate_uuid():
    return uuid.uuid4().hex

def slugify_key(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s-]+', '_', text)
    return text or "field"

class CustomFieldDefinition(Base):
    __tablename__ = "custom_field_definitions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False)  # 'contact', 'opportunity', 'company'
    label = Column(String(100), nullable=False)
    field_key = Column(String(100), nullable=False)
    field_type = Column(String(32), default="text", nullable=False)  # 'text', 'number', 'select'
    options = Column(JSON, default=list, nullable=False)  # list of strings for select

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "entity_type", "field_key", name="uq_workspace_entity_field_key"),
    )

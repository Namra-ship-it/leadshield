import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return uuid.uuid4().hex

class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"

class EmployeeStatus(str, enum.Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    ON_LEAVE = "on_leave"
    OFFLINE = "offline"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default=UserRole.USER.value, nullable=False)
    status = Column(String(32), default=EmployeeStatus.AVAILABLE.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    phone = Column(String(64), nullable=True)
    telegram_chat_id = Column(String(64), nullable=True)
    last_assigned_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="users")

    # Enforce uniqueness of email within a workspace, or globally
    __table_args__ = (
        UniqueConstraint("email", "workspace_id", name="uq_user_email_workspace"),
    )

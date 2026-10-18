import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return uuid.uuid4().hex

class SyncHistory(Base):
    """
    Append-only audit and observability log for every inbound and outbound
    provider adapter interaction.
    """
    __tablename__ = "sync_history"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Provider categorization
    provider_type = Column(String(32), nullable=False, index=True) # messaging, payment, calendar, notify
    provider_name = Column(String(64), nullable=False, index=True) # mock_whatsapp, stripe_test, etc.
    direction = Column(String(16), nullable=False)                 # inbound, outbound
    action = Column(String(64), nullable=False)                    # send_message, webhook_received, etc.
    event_id = Column(String(255), nullable=True, index=True)      # for idempotency correlation

    # Status and telemetry
    status = Column(String(32), nullable=False, index=True)        # success, error
    status_code = Column(Integer, nullable=True)
    payload_summary = Column(JSON, default=dict, nullable=False)
    response_summary = Column(JSON, default=dict, nullable=False)
    error_message = Column(String(1000), nullable=True)
    latency_ms = Column(Integer, default=0, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    workspace = relationship("Workspace")

class ProcessedEvent(Base):
    """
    Idempotency store to guarantee at-most-once processing for webhooks and provider events.
    """
    __tablename__ = "processed_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workspace_id = Column(String(36), nullable=True, index=True)
    provider_name = Column(String(64), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(64), nullable=True)
    response_data = Column(JSON, default=dict, nullable=False)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("provider_name", "event_id", name="uq_provider_event_id"),
    )

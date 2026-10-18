import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.integration import SyncHistory, ProcessedEvent

logger = logging.getLogger("adapters")

def retry_with_backoff(
    fn: Callable,
    retries: int = 3,
    base_delay: float = 0.3,
    backoff_factor: float = 2.0,
    max_delay: float = 3.0,
    allowed_exceptions: tuple = (Exception,)
):
    """
    Synchronous retry with exponential backoff.
    Ensures network glitches to third-party APIs don't cause immediate failure.
    """
    delay = base_delay
    last_exc = None
    for attempt in range(retries):
        try:
            return fn(), attempt
        except allowed_exceptions as exc:
            last_exc = exc
            if attempt == retries - 1:
                break
            time.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    raise last_exc

def log_sync_call(
    provider_type: str,
    provider_name: str,
    direction: str,
    action: str,
    status: str,
    latency_ms: int,
    workspace_id: Optional[str] = None,
    event_id: Optional[str] = None,
    status_code: Optional[int] = None,
    payload_summary: Optional[Dict[str, Any]] = None,
    response_summary: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    retry_count: int = 0,
    db: Optional[Session] = None
) -> SyncHistory:
    """
    Records an entry in the sync_history audit log table.
    Can use an existing DB session or create an isolated one.
    """
    close_db = False
    if db is None:
        from app.core.database import get_current_db_session
        db = get_current_db_session()
        if db is None:
            db = SessionLocal()
            close_db = True

    try:
        record = SyncHistory(
            workspace_id=workspace_id,
            provider_type=provider_type,
            provider_name=provider_name,
            direction=direction,
            action=action,
            event_id=str(event_id) if event_id else None,
            status=status,
            status_code=status_code,
            payload_summary=payload_summary or {},
            response_summary=response_summary or {},
            error_message=str(error_message)[:1000] if error_message else None,
            latency_ms=latency_ms,
            retry_count=retry_count,
            created_at=datetime.now(timezone.utc)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception as e:
        logger.error(f"Failed to record sync history: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None
    finally:
        if close_db:
            db.close()

def check_idempotency(db: Session, provider_name: str, event_id: str) -> Optional[Dict[str, Any]]:
    """
    Checks if an event has already been processed.
    Returns the cached response data if already processed, else None.
    """
    if not event_id:
        return None
    rec = db.query(ProcessedEvent).filter(
        ProcessedEvent.provider_name == provider_name,
        ProcessedEvent.event_id == event_id
    ).first()
    if rec:
        return rec.response_data or {"status": "already_processed", "event_id": event_id}
    return None

def mark_event_processed(
    db: Session,
    provider_name: str,
    event_id: str,
    event_type: Optional[str] = None,
    workspace_id: Optional[str] = None,
    response_data: Optional[Dict[str, Any]] = None
) -> ProcessedEvent:
    """
    Marks an event as processed in the database for deduplication.
    """
    rec = ProcessedEvent(
        workspace_id=workspace_id,
        provider_name=provider_name,
        event_id=event_id,
        event_type=event_type,
        response_data=response_data or {},
        processed_at=datetime.now(timezone.utc)
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

class BaseAdapter(ABC):
    """
    Base contract for all external integration adapters.
    """
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Category: messaging | payment | calendar | notify"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier: mock_whatsapp, stripe_test, etc."""
        pass

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """True if this is a simulation adapter displaying a 'MOCK' badge."""
        pass

    @property
    def is_configured(self) -> bool:
        """True if required API keys/tokens are present."""
        return True

    @abstractmethod
    def get_limits_note(self) -> str:
        """Plain-language description of provider quotas and limits."""
        pass

    def get_status(self, db: Session, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates adapter health, last success, and last error from sync history.
        """
        query = db.query(SyncHistory).filter(
            SyncHistory.provider_name == self.name
        )
        if workspace_id:
            query = query.filter((SyncHistory.workspace_id == workspace_id) | (SyncHistory.workspace_id.is_(None)))

        last_success = query.filter(SyncHistory.status == "success").order_by(SyncHistory.created_at.desc()).first()
        last_error = query.filter(SyncHistory.status == "error").order_by(SyncHistory.created_at.desc()).first()

        total_calls = query.count()
        error_calls = query.filter(SyncHistory.status == "error").count()
        success_rate = 100.0 if total_calls == 0 else round(((total_calls - error_calls) / total_calls) * 100, 1)

        return {
            "provider_type": self.provider_type,
            "provider_name": self.name,
            "is_mock": self.is_mock,
            "is_configured": self.is_configured,
            "limits_note": self.get_limits_note(),
            "total_calls": total_calls,
            "success_rate": success_rate,
            "last_success_at": last_success.created_at.isoformat() if last_success else None,
            "last_error_at": last_error.created_at.isoformat() if last_error else None,
            "last_error_message": last_error.error_message if last_error else None,
            "operational": True
        }

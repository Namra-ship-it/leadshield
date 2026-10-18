import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.integration import SyncHistory
from app.adapters.factory import (
    get_all_adapters_status,
    get_messaging_adapter,
    get_payment_adapter,
    get_calendar_adapter,
    get_notify_adapter
)
from app.adapters.base import log_sync_call

logger = logging.getLogger("api.integrations")
router = APIRouter(prefix="/integrations", tags=["Integrations & Adapters"])

@router.get("/status")
def get_integrations_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns live health, last success, last error, limits note, and MOCK badge status
    for all 4 active provider adapters.
    """
    return get_all_adapters_status(db, current_user.workspace_id)

@router.get("/sync-history")
def get_sync_history(
    provider_type: Optional[str] = None,
    provider_name: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Paginated audit log of every inbound & outbound provider adapter call.
    Includes status, latency, request/response payload summaries, and error logs.
    """
    query = db.query(SyncHistory).filter(
        (SyncHistory.workspace_id == current_user.workspace_id) | (SyncHistory.workspace_id.is_(None))
    )

    if provider_type:
        query = query.filter(SyncHistory.provider_type == provider_type)
    if provider_name:
        query = query.filter(SyncHistory.provider_name == provider_name)
    if status:
        query = query.filter(SyncHistory.status == status)

    total = query.count()
    items = query.order_by(desc(SyncHistory.created_at)).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1,
        "items": [
            {
                "id": it.id,
                "provider_type": it.provider_type,
                "provider_name": it.provider_name,
                "direction": it.direction,
                "action": it.action,
                "event_id": it.event_id,
                "status": it.status,
                "status_code": it.status_code,
                "payload_summary": it.payload_summary,
                "response_summary": it.response_summary,
                "error_message": it.error_message,
                "latency_ms": it.latency_ms,
                "retry_count": it.retry_count,
                "created_at": (it.created_at.replace(tzinfo=timezone.utc) if it.created_at.tzinfo is None else it.created_at).isoformat()
            }
            for it in items
        ]
    }

@router.post("/test/{provider_type}")
def test_provider_connection(
    provider_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes a health check test call against the selected provider adapter.
    """
    ws_id = current_user.workspace_id
    if provider_type == "messaging":
        adapter = get_messaging_adapter()
        result = adapter.send_message(
            to="+15550001122",
            text="[LeadGuard Test] Ping from integrations dashboard.",
            workspace_id=ws_id
        )
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(
                status_code=result.get("status_code", 400),
                detail=result.get("detail", "Messaging provider error")
            )
        return {"status": "ok", "provider": adapter.name, "result": result}
    elif provider_type == "payment":
        adapter = get_payment_adapter()
        result = adapter.create_payment_link(
            amount=100.0,
            currency="USD",
            description="Test payment link verification",
            metadata={"test": "true", "workspace_id": ws_id},
            workspace_id=ws_id
        )
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(
                status_code=result.get("status_code", 400),
                detail=result.get("detail", "Payment provider error")
            )
        return {"status": "ok", "provider": adapter.name, "result": result}
    elif provider_type == "calendar":
        adapter = get_calendar_adapter()
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        result = adapter.get_free_busy(
            start_time=now,
            end_time=now + timedelta(days=1),
            user_email_or_id=current_user.id,
            workspace_id=ws_id
        )
        return {
            "status": "ok",
            "provider": adapter.name,
            "result": {
                "busy_slots": result,
                "read_only_check": True,
                "checked_at": now.isoformat()
            }
        }
    elif provider_type == "notify":
        adapter = get_notify_adapter()
        result = adapter.send_notification(
            title="Integrations Test Alert",
            message=f"Manual connection check executed by {current_user.full_name}.",
            metadata={"user_id": current_user.id},
            workspace_id=ws_id
        )
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(
                status_code=result.get("status_code", 400),
                detail=result.get("detail", "Notification provider error")
            )
        return {"status": "ok", "provider": adapter.name, "result": result}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider type: {provider_type}")

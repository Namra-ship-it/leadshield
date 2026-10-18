import json
import asyncio
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.events import event_broadcaster
from app.data_access.user_repo import user_repo

router = APIRouter(prefix="/events", tags=["Real-Time Events"])

@router.get("/stream")
async def event_stream(
    token: str = Query(..., description="JWT token for EventSource authentication"),
    db: Session = Depends(get_db)
):
    """
    SERVER-SENT EVENTS (SSE) STREAM:
    Real-time push notifications for lead arrivals, live countdowns,
    escalation transfers, reassignment, and recovery queue updates.
    """
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    workspace_id = payload.get("workspace_id")
    if not user_id or not workspace_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = user_repo.get_by_id(db, user_id=user_id, workspace_id=workspace_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    queue = event_broadcaster.subscribe(workspace_id)

    async def stream_generator():
        # Initial connection event
        yield f"event: connected\ndata: {json.dumps({'message': 'Connected to Lead Protection Real-Time Stream', 'workspace_id': workspace_id})}\n\n"
        try:
            while True:
                try:
                    # Wait for next event or 15s keepalive
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep HTTP connection alive
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_broadcaster.unsubscribe(workspace_id, queue)

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

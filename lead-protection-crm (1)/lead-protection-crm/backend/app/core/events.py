import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Any

logger = logging.getLogger("events")

class EventBroadcaster:
    def __init__(self):
        # Maps workspace_id -> set of asyncio.Queue
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._loop: asyncio.AbstractEventLoop = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def subscribe(self, workspace_id: str) -> asyncio.Queue:
        if workspace_id not in self._subscribers:
            self._subscribers[workspace_id] = set()
        queue = asyncio.Queue(maxsize=100)
        self._subscribers[workspace_id].add(queue)
        logger.info(f"Client subscribed to workspace {workspace_id} events. Total listeners: {len(self._subscribers[workspace_id])}")
        return queue

    def unsubscribe(self, workspace_id: str, queue: asyncio.Queue):
        if workspace_id in self._subscribers:
            self._subscribers[workspace_id].discard(queue)
            if not self._subscribers[workspace_id]:
                del self._subscribers[workspace_id]
            logger.info(f"Client unsubscribed from workspace {workspace_id} events.")

    def broadcast_sync(self, workspace_id: str, event_type: str, data: Any):
        """
        Thread-safe broadcast helper that can be called from synchronous endpoints
        and APScheduler background worker threads.
        """
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if workspace_id not in self._subscribers or not self._subscribers[workspace_id]:
            return

        for queue in list(self._subscribers[workspace_id]):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass
            except Exception as e:
                logger.debug(f"Error pushing event to queue: {e}")

event_broadcaster = EventBroadcaster()

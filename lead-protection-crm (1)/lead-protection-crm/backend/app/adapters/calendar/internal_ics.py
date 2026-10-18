import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.adapters.calendar.base import CalendarAdapter
from app.adapters.base import log_sync_call

class InternalIcsAdapter(CalendarAdapter):
    """
    Internal calendar adapter generating RFC 5545 iCalendar (.ics) files and
    managing database-backed appointments with overlap detection.
    """
    def __init__(self):
        # In-memory store for fallback/demo, or synchronizes with appointment table
        self._events: Dict[str, Dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "internal_ics"

    @property
    def is_mock(self) -> bool:
        return True

    def get_limits_note(self) -> str:
        return "Internal RFC 5545 Engine: Zero API limits. Generates standardized .ics invitations compatible with Google Calendar, Outlook, and Apple Mail."

    def export_ics(self, event_data: Dict[str, Any]) -> str:
        uid = event_data.get("event_id") or f"leadguard_{uuid.uuid4().hex}"
        now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        
        start = event_data.get("start_time")
        if isinstance(start, str):
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        start_str = start.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        end = event_data.get("end_time")
        if isinstance(end, str):
            end = datetime.fromisoformat(end.replace("Z", "+00:00"))
        end_str = end.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        title = event_data.get("title", "Lead Consultation")
        desc = event_data.get("description", "Scheduled via LeadGuard CRM")

        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//LeadGuard CRM//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        return "\r\n".join(ics_lines)

    def get_free_busy(
        self,
        start_time: datetime,
        end_time: datetime,
        user_email_or_id: str,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        t0 = time.time()
        busy_slots = []
        for ev in self._events.values():
            if ev.get("user_id") == user_email_or_id or not user_email_or_id:
                ev_start = ev["start_time"]
                ev_end = ev["end_time"]
                if not (ev_end <= start_time or ev_start >= end_time):
                    busy_slots.append({
                        "start": ev_start.isoformat(),
                        "end": ev_end.isoformat(),
                        "title": ev.get("title")
                    })
        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type=self.provider_type,
            provider_name=self.name,
            direction="inbound",
            action="get_free_busy",
            status="success",
            status_code=200,
            workspace_id=workspace_id,
            payload_summary={"user": user_email_or_id, "start": start_time.isoformat(), "end": end_time.isoformat()},
            response_summary={"busy_count": len(busy_slots)},
            latency_ms=latency
        )
        return busy_slots

    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: str = "",
        user_email_or_id: str = "",
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        # Check overlaps
        busy = self.get_free_busy(start_time, end_time, user_email_or_id, workspace_id)
        if busy:
            latency = int((time.time() - t0) * 1000)
            err_msg = "Time slot overlap: User is already booked during this time"
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="create_event",
                status="error",
                status_code=409,
                workspace_id=workspace_id,
                payload_summary={"title": title, "user": user_email_or_id},
                error_message=err_msg,
                latency_ms=latency
            )
            return {"status": "error", "detail": err_msg}

        event_id = f"ics_evt_{uuid.uuid4().hex[:12]}"
        event_dict = {
            "event_id": event_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
            "description": description,
            "user_id": user_email_or_id,
            "workspace_id": workspace_id,
            "status": "confirmed"
        }
        event_dict["ics_content"] = self.export_ics(event_dict)
        self._events[event_id] = event_dict

        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type=self.provider_type,
            provider_name=self.name,
            direction="outbound",
            action="create_event",
            status="success",
            status_code=201,
            event_id=event_id,
            workspace_id=workspace_id,
            payload_summary={"title": title, "user": user_email_or_id, "start": start_time.isoformat()},
            response_summary={"event_id": event_id, "status": "confirmed"},
            latency_ms=latency
        )
        return event_dict

    def cancel_event(
        self,
        event_id: str,
        user_email_or_id: str = "",
        workspace_id: Optional[str] = None
    ) -> bool:
        t0 = time.time()
        if event_id in self._events:
            del self._events[event_id]
            latency = int((time.time() - t0) * 1000)
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="cancel_event",
                status="success",
                status_code=200,
                event_id=event_id,
                workspace_id=workspace_id,
                response_summary={"status": "cancelled"},
                latency_ms=latency
            )
            return True
        return False

    def reschedule_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        user_email_or_id: str = "",
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        if event_id not in self._events:
            return {"status": "error", "detail": "Event not found"}
        
        event = self._events[event_id]
        event["start_time"] = new_start
        event["end_time"] = new_end
        event["ics_content"] = self.export_ics(event)

        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type=self.provider_type,
            provider_name=self.name,
            direction="outbound",
            action="reschedule_event",
            status="success",
            status_code=200,
            event_id=event_id,
            workspace_id=workspace_id,
            payload_summary={"new_start": new_start.isoformat(), "new_end": new_end.isoformat()},
            response_summary={"status": "rescheduled"},
            latency_ms=latency
        )
        return event

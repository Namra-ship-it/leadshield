from abc import abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.adapters.base import BaseAdapter

class CalendarAdapter(BaseAdapter):
    @property
    def provider_type(self) -> str:
        return "calendar"

    @abstractmethod
    def get_free_busy(
        self,
        start_time: datetime,
        end_time: datetime,
        user_email_or_id: str,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns list of busy time intervals: [{"start": iso_str, "end": iso_str}]
        """
        pass

    @abstractmethod
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
        """
        Schedules a calendar event. Returns event details with event_id, start, end, ics_data.
        """
        pass

    @abstractmethod
    def cancel_event(
        self,
        event_id: str,
        user_email_or_id: str = "",
        workspace_id: Optional[str] = None
    ) -> bool:
        """
        Cancels a scheduled calendar appointment.
        """
        pass

    @abstractmethod
    def reschedule_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        user_email_or_id: str = "",
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reschedules an appointment to a new time window.
        """
        pass

    @abstractmethod
    def export_ics(self, event_data: Dict[str, Any]) -> str:
        """
        Generates RFC 5545 compliant .ics iCalendar file string.
        """
        pass

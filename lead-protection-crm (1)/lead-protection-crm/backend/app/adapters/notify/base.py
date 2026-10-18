from abc import abstractmethod
from typing import Optional, Dict, Any
from app.adapters.base import BaseAdapter

class NotifyAdapter(BaseAdapter):
    @property
    def provider_type(self) -> str:
        return "notify"

    @abstractmethod
    def send_notification(
        self,
        title: str,
        message: str,
        destination: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delivers an escalation or team alert.
        Returns status dictionary with notification_id and delivery confirmation.
        """
        pass

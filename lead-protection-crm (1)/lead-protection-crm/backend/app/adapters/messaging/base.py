from abc import abstractmethod
from typing import Optional, Dict, Any
from app.adapters.base import BaseAdapter

class MessagingAdapter(BaseAdapter):
    @property
    def provider_type(self) -> str:
        return "messaging"

    @abstractmethod
    def send_message(self, to: str, text: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send outbound messaging message (e.g. WhatsApp / Telegram).
        Returns dictionary containing message_id, status, and raw response.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """
        Validates cryptographic HMAC or header token on incoming webhook requests.
        """
        pass

    @abstractmethod
    def parse_inbound_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts sender, message text, message_id, and metadata from raw webhook payload.
        Returns None if payload is not an inbound customer message (e.g. delivery receipts).
        """
        pass

from abc import abstractmethod
from typing import Optional, Dict, Any
from app.adapters.base import BaseAdapter

class PaymentAdapter(BaseAdapter):
    @property
    def provider_type(self) -> str:
        return "payment"

    @abstractmethod
    def create_payment_link(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a payment checkout link or session.
        Returns dictionary with payment_id, checkout_url, amount, currency, and status.
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """
        Verifies cryptographic HMAC signature on incoming payment gateway webhooks.
        """
        pass

    @abstractmethod
    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts event_id, event_type, payment_id, amount, currency, customer info, and metadata.
        """
        pass

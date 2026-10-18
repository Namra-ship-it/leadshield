import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from app.adapters.messaging.base import MessagingAdapter
from app.adapters.base import log_sync_call

class MockWhatsAppAdapter(MessagingAdapter):
    """
    Mock WhatsApp adapter for development, testing, and sandbox demonstrations.
    Simulates inbound & outbound WhatsApp messaging with full sync history tracking.
    """
    def __init__(self):
        self._sent_messages: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "mock_whatsapp"

    @property
    def is_mock(self) -> bool:
        return True

    def get_limits_note(self) -> str:
        return "MOCK Sandbox Mode: Unlimited simulated messages. Zero cost, no API keys or Meta Business verification needed. Fully idempotent."

    def send_message(self, to: str, text: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        t0 = time.time()
        msg_id = f"mock_wa_msg_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        record = {
            "message_id": msg_id,
            "to": to,
            "text": text,
            "status": "delivered",
            "timestamp": now.isoformat()
        }
        self._sent_messages.append(record)

        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type=self.provider_type,
            provider_name=self.name,
            direction="outbound",
            action="send_message",
            status="success",
            status_code=200,
            event_id=msg_id,
            workspace_id=workspace_id,
            payload_summary={"to": to, "text_preview": text[:100]},
            response_summary={"status": "delivered", "message_id": msg_id},
            latency_ms=latency
        )
        return record

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        # For mock adapter, check if mock signature header is provided or allow test calls
        sig = headers.get("x-mock-signature") or headers.get("X-Mock-Signature")
        if sig == "invalid_sig":
            return False
        return True

    def parse_inbound_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses inbound message from mock JSON payload:
        {
            "from": "+919876543210",
            "body": "Hello, need pricing",
            "message_id": "msg_123",
            "name": "Alex"
        }
        """
        if not payload:
            return None
        
        sender = payload.get("from") or payload.get("sender") or payload.get("phone")
        text = payload.get("body") or payload.get("text") or payload.get("message")
        if not sender or text is None:
            return None

        sender_name = payload.get("name") or payload.get("sender_name") or "WhatsApp User"
        from app.core.phone import normalize_phone_e164
        normalized_sender = normalize_phone_e164(str(sender)) or str(sender)
        msg_id = payload.get("message_id") or payload.get("id") or f"mock_in_{uuid.uuid4().hex[:10]}"
        return {
            "event_id": str(msg_id),
            "sender_phone": normalized_sender,
            "sender_name": str(sender_name),
            "text": str(text).strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw": payload
        }

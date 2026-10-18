import time
import hmac
import hashlib
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.messaging.base import MessagingAdapter
from app.adapters.base import log_sync_call, retry_with_backoff
from app.core.config import settings

logger = logging.getLogger("adapters.meta_whatsapp")

class MetaWhatsAppCloudAdapter(MessagingAdapter):
    """
    Real Meta WhatsApp Cloud API integration using official Graph API endpoints.
    Handles test number / production WhatsApp Business Accounts with HMAC-SHA256 signature verification.
    """
    @property
    def name(self) -> str:
        return "meta_whatsapp_cloud"

    @property
    def is_mock(self) -> bool:
        return False

    def get_limits_note(self) -> str:
        return "Meta WhatsApp Cloud API: 1,000 free service conversations/month; 80 msg/sec standard rate limit. 24-hour customer service window applies to freeform replies."

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        secret = settings.META_WA_APP_SECRET
        if not secret:
            # If secret not set in test environment, reject untrusted webhooks
            logger.warning("META_WA_APP_SECRET is not configured; rejecting webhook")
            return False

        signature_header = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256")
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        received_sig = signature_header.split("sha256=")[1]
        return hmac.compare_digest(expected_sig, received_sig)

    def verify_challenge(self, mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Optional[str]:
        """
        Meta WhatsApp webhook handshake verification (GET request).
        """
        if mode == "subscribe" and token == settings.META_WA_VERIFY_TOKEN:
            return challenge
        return None

    def send_message(self, to: str, text: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        t0 = time.time()
        phone_id = settings.META_WA_PHONE_NUMBER_ID
        token = settings.META_WA_ACCESS_TOKEN

        # Clean recipient phone number (remove +, spaces, hyphens)
        clean_to = "".join(ch for ch in to if ch.isdigit())

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {"preview_url": False, "body": text}
        }

        if not phone_id or not token:
            latency = int((time.time() - t0) * 1000)
            err_msg = "META_WA_PHONE_NUMBER_ID or META_WA_ACCESS_TOKEN not configured"
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_message",
                status="error",
                status_code=500,
                workspace_id=workspace_id,
                payload_summary={"to": to, "text_preview": text[:100]},
                error_message=err_msg,
                latency_ms=latency
            )
            return {"status": "error", "detail": err_msg}

        url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        def _do_post():
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                return res.json(), res.status_code

        try:
            (res_json, status_code), retries = retry_with_backoff(_do_post, retries=3, base_delay=0.3)
            latency = int((time.time() - t0) * 1000)
            msg_id = res_json.get("messages", [{}])[0].get("id")

            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_message",
                status="success",
                status_code=status_code,
                event_id=msg_id,
                workspace_id=workspace_id,
                payload_summary={"to": to, "text_preview": text[:100]},
                response_summary=res_json,
                latency_ms=latency,
                retry_count=retries
            )
            return {
                "message_id": msg_id,
                "status": "sent",
                "raw": res_json
            }
        except Exception as exc:
            latency = int((time.time() - t0) * 1000)
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_message",
                status="error",
                status_code=502,
                workspace_id=workspace_id,
                payload_summary={"to": to, "text_preview": text[:100]},
                error_message=str(exc),
                latency_ms=latency,
                retry_count=2
            )
            logger.error(f"Meta WhatsApp outbound error: {exc}")
            return {"status": "error", "detail": str(exc)}

    def parse_inbound_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses Meta Graph API messages payload.
        Returns extracted sender, text, message_id or None if not an incoming message.
        """
        try:
            entry = payload.get("entry", [])[0]
            change = entry.get("changes", [])[0]
            val = change.get("value", {})
            messages = val.get("messages", [])
            if not messages:
                return None
            
            msg = messages[0]
            if msg.get("type") != "text":
                return None

            contacts = val.get("contacts", [{}])
            sender_name = contacts[0].get("profile", {}).get("name", "WhatsApp User")
            sender_phone = msg.get("from")
            text = msg.get("text", {}).get("body", "")
            msg_id = msg.get("id")

            from app.core.phone import normalize_phone_e164
            norm_phone = normalize_phone_e164(sender_phone) or str(sender_phone)

            return {
                "event_id": str(msg_id),
                "sender_phone": norm_phone,
                "sender_name": sender_name,
                "text": text.strip(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw": payload
            }
        except (IndexError, KeyError, TypeError) as e:
            logger.debug(f"Non-message Meta WhatsApp webhook payload: {e}")
            return None

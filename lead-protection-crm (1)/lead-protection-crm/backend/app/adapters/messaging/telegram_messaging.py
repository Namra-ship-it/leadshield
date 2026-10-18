import time
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.messaging.base import MessagingAdapter
from app.adapters.base import log_sync_call, retry_with_backoff
from app.core.config import settings

logger = logging.getLogger("adapters.telegram_messaging")

class TelegramMessagingAdapter(MessagingAdapter):
    """
    Telegram Bot API adapter for customer & team messaging.
    """
    @property
    def name(self) -> str:
        return "telegram"

    @property
    def is_mock(self) -> bool:
        return False

    @property
    def is_configured(self) -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_DEFAULT_CHAT_ID)

    def get_limits_note(self) -> str:
        return "Telegram Bot API: 30 messages/sec globally; max 1 message/sec per private user chat. 4,096 char message limit. Webhook token validation."

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        secret = settings.TELEGRAM_WEBHOOK_SECRET
        if not secret:
            return True
        secret_header = headers.get("x-telegram-bot-api-secret-token") or headers.get("X-Telegram-Bot-Api-Secret-Token")
        return secret_header == secret

    def send_message(self, to: str, text: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        t0 = time.time()
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = to or settings.TELEGRAM_DEFAULT_CHAT_ID

        if not token or not chat_id:
            latency = int((time.time() - t0) * 1000)
            err_msg = "Telegram bot token or chat ID is not configured"
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_message",
                status="error",
                status_code=400,
                workspace_id=workspace_id,
                payload_summary={"chat_id": chat_id, "text_preview": text[:100]},
                error_message="not configured",
                latency_ms=latency
            )
            return {"status": "error", "status_code": 400, "detail": err_msg}

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        def _do_post():
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                return res.json(), res.status_code

        try:
            (res_json, status_code), retries = retry_with_backoff(_do_post, retries=3, base_delay=0.3)
            latency = int((time.time() - t0) * 1000)
            msg_id = str(res_json.get("result", {}).get("message_id"))

            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_message",
                status="success",
                status_code=status_code,
                event_id=msg_id,
                workspace_id=workspace_id,
                payload_summary={"chat_id": chat_id, "text_preview": text[:100]},
                response_summary=res_json,
                latency_ms=latency,
                retry_count=retries
            )
            return {"message_id": msg_id, "status": "sent", "raw": res_json}
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
                payload_summary={"chat_id": chat_id, "text_preview": text[:100]},
                error_message=str(exc),
                latency_ms=latency,
                retry_count=2
            )
            logger.error(f"Telegram messaging error: {exc}")
            return {"status": "error", "detail": str(exc)}

    def parse_inbound_message(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        message = payload.get("message") or payload.get("edited_message")
        if not message:
            return None

        text = message.get("text", "")
        sender = message.get("from", {})
        chat = message.get("chat", {})
        update_id = payload.get("update_id")

        contact_info = message.get("contact") or {}
        raw_phone = contact_info.get("phone_number")
        sender_phone = str(chat.get("id"))
        if raw_phone:
            from app.core.phone import normalize_phone_e164
            norm = normalize_phone_e164(raw_phone)
            if norm:
                sender_phone = norm

        return {
            "event_id": str(update_id or message.get("message_id")),
            "sender_phone": sender_phone,
            "sender_name": f"{sender.get('first_name', '')} {sender.get('last_name', '')}".strip() or "Telegram User",
            "text": text.strip(),
            "chat_id": str(chat.get("id")),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw": payload
        }

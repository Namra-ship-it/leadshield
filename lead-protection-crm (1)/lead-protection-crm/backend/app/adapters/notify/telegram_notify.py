import time
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.notify.base import NotifyAdapter
from app.adapters.base import log_sync_call, retry_with_backoff
from app.core.config import settings

logger = logging.getLogger("adapters.telegram_notify")

class TelegramNotifyAdapter(NotifyAdapter):
    """
    Delivers urgent escalation alerts, acknowledgement warnings, and team notifications via Telegram.
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
        return "Telegram Bot API: 30 messages/sec globally. Instant push notifications for team escalations and SLA timers."

    def send_notification(
        self,
        title: str,
        message: str,
        destination: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = destination or settings.TELEGRAM_DEFAULT_CHAT_ID

        formatted_text = f"<b>🚨 {title}</b>\n\n{message}"
        if metadata:
            lead_id = metadata.get("lead_id")
            if lead_id:
                formatted_text += f"\n\n👉 <i>Lead ID: <code>{lead_id}</code></i>"

        if not token or not chat_id:
            latency = int((time.time() - t0) * 1000)
            err_msg = "Telegram bot token or destination chat ID is not configured"
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_notification",
                status="error",
                status_code=400,
                workspace_id=workspace_id,
                payload_summary={"title": title, "chat_id": chat_id},
                error_message="not configured",
                latency_ms=latency
            )
            return {"status": "error", "status_code": 400, "detail": err_msg}

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": formatted_text,
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
                action="send_notification",
                status="success",
                status_code=status_code,
                event_id=msg_id,
                workspace_id=workspace_id,
                payload_summary={"title": title, "chat_id": chat_id},
                response_summary=res_json,
                latency_ms=latency,
                retry_count=retries
            )
            return {"status": "delivered", "notification_id": msg_id, "raw": res_json}
        except Exception as exc:
            latency = int((time.time() - t0) * 1000)
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_notification",
                status="error",
                status_code=502,
                workspace_id=workspace_id,
                payload_summary={"title": title, "chat_id": chat_id},
                error_message=str(exc),
                latency_ms=latency,
                retry_count=2
            )
            logger.error(f"Telegram notification error: {exc}")
            return {"status": "error", "detail": str(exc)}

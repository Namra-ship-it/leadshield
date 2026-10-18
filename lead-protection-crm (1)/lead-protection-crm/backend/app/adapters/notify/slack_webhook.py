import time
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.notify.base import NotifyAdapter
from app.adapters.base import log_sync_call, retry_with_backoff
from app.core.config import settings

logger = logging.getLogger("adapters.slack_webhook")

class SlackWebhookAdapter(NotifyAdapter):
    """
    Delivers team alerts and escalation notices to Slack channels using incoming webhooks.
    """
    @property
    def name(self) -> str:
        return "slack_webhook"

    @property
    def is_mock(self) -> bool:
        return False

    def get_limits_note(self) -> str:
        return "Slack Incoming Webhook: 1 message/sec rate limit. Rich card notifications formatted with Slack Block Kit."

    def send_notification(
        self,
        title: str,
        message: str,
        destination: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        webhook_url = destination or settings.SLACK_WEBHOOK_URL

        if not webhook_url:
            latency = int((time.time() - t0) * 1000)
            err_msg = "SLACK_WEBHOOK_URL not configured"
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_notification",
                status="error",
                status_code=500,
                workspace_id=workspace_id,
                payload_summary={"title": title},
                error_message=err_msg,
                latency_ms=latency
            )
            return {"status": "error", "detail": err_msg}

        payload = {
            "text": f"*{title}*\n{message}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🚨 {title}", "emoji": True}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message}
                }
            ]
        }

        def _do_post():
            with httpx.Client(timeout=10.0) as client:
                res = client.post(webhook_url, json=payload)
                res.raise_for_status()
                return res.text, res.status_code

        try:
            (res_text, status_code), retries = retry_with_backoff(_do_post, retries=3, base_delay=0.3)
            latency = int((time.time() - t0) * 1000)

            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_notification",
                status="success",
                status_code=status_code,
                workspace_id=workspace_id,
                payload_summary={"title": title},
                response_summary={"response": res_text},
                latency_ms=latency,
                retry_count=retries
            )
            return {"status": "delivered", "response": res_text}
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
                payload_summary={"title": title},
                error_message=str(exc),
                latency_ms=latency,
                retry_count=2
            )
            logger.error(f"Slack webhook error: {exc}")
            return {"status": "error", "detail": str(exc)}

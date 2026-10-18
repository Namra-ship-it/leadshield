import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.notify.base import NotifyAdapter
from app.adapters.base import log_sync_call
from app.core.config import settings

logger = logging.getLogger("adapters.smtp_email")

class SmtpEmailAdapter(NotifyAdapter):
    """
    Standard SMTP email notification adapter for lead notifications and manager escalations.
    """
    @property
    def name(self) -> str:
        return "smtp_email"

    @property
    def is_mock(self) -> bool:
        return False

    def get_limits_note(self) -> str:
        return "Standard SMTP Email: 500-10,000 emails/day depending on relay host (e.g. SendGrid, Amazon SES, or Gmail SMTP). Full HTML templates supported."

    def send_notification(
        self,
        title: str,
        message: str,
        destination: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        to_email = destination or settings.SMTP_FROM_EMAIL
        from_email = settings.SMTP_FROM_EMAIL

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = f"[LeadGuard Alert] {title}"

        html_body = f"""
        <html>
        <body style="font-family: sans-serif; background-color: #0f172a; color: #f8fafc; padding: 24px;">
            <div style="background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; padding: 24px; max-width: 600px;">
                <h2 style="color: #f43f5e; margin-top: 0;">🚨 {title}</h2>
                <p style="font-size: 16px; line-height: 1.5;">{message}</p>
                <div style="margin-top: 20px; padding: 12px; background-color: #0f172a; border-radius: 6px; font-family: monospace; font-size: 13px;">
                    Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        try:
            # If default localhost or test environment without live mail server, simulate or connect
            if settings.SMTP_HOST in ["localhost", "127.0.0.1"] and not settings.SMTP_USER:
                # Local dev test simulation
                latency = int((time.time() - t0) * 1000)
                log_sync_call(
                    provider_type=self.provider_type,
                    provider_name=self.name,
                    direction="outbound",
                    action="send_notification",
                    status="success",
                    status_code=200,
                    workspace_id=workspace_id,
                    payload_summary={"to": to_email, "title": title},
                    response_summary={"status": "queued_local_relay"},
                    latency_ms=latency
                )
                return {"status": "delivered", "method": "local_relay"}

            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            latency = int((time.time() - t0) * 1000)
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_notification",
                status="success",
                status_code=200,
                workspace_id=workspace_id,
                payload_summary={"to": to_email, "title": title},
                response_summary={"status": "smtp_sent"},
                latency_ms=latency
            )
            return {"status": "delivered", "method": "smtp"}
        except Exception as exc:
            latency = int((time.time() - t0) * 1000)
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="send_notification",
                status="error",
                status_code=500,
                workspace_id=workspace_id,
                payload_summary={"to": to_email, "title": title},
                error_message=str(exc),
                latency_ms=latency
            )
            logger.error(f"SMTP error: {exc}")
            return {"status": "error", "detail": str(exc)}

import time
import hmac
import hashlib
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.payments.base import PaymentAdapter
from app.adapters.base import log_sync_call, retry_with_backoff
from app.core.config import settings

logger = logging.getLogger("adapters.razorpay_test")

class RazorpayTestAdapter(PaymentAdapter):
    """
    Razorpay Test Mode integration for Indian and international payment links with webhook verification.
    """
    @property
    def name(self) -> str:
        return "razorpay_test"

    @property
    def is_mock(self) -> bool:
        return False

    def get_limits_note(self) -> str:
        return "Razorpay Test Sandbox: 10 requests/sec API limit. Supports UPI, NetBanking, and credit/debit test cards with real-time test webhooks."

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not secret:
            logger.warning("RAZORPAY_WEBHOOK_SECRET not configured; rejecting webhook")
            return False

        sig = headers.get("x-razorpay-signature") or headers.get("X-Razorpay-Signature")
        if not sig:
            return False

        expected_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, sig)

    def create_payment_link(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        key_id = settings.RAZORPAY_KEY_ID
        key_secret = settings.RAZORPAY_KEY_SECRET

        if not key_id or not key_secret:
            latency = int((time.time() - t0) * 1000)
            err_msg = "RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not configured"
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="create_payment_link",
                status="error",
                status_code=500,
                workspace_id=workspace_id,
                payload_summary={"amount": amount, "currency": currency},
                error_message=err_msg,
                latency_ms=latency
            )
            return {"status": "error", "detail": err_msg}

        url = "https://api.razorpay.com/v1/payment_links"
        auth = (key_id, key_secret)

        amount_in_paise = int(amount * 100)
        payload = {
            "amount": amount_in_paise,
            "currency": currency.upper(),
            "accept_partial": False,
            "description": description or "CRM Lead Guard Invoice",
            "notes": {str(k): str(v) for k, v in (metadata or {}).items()}
        }

        def _do_post():
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, auth=auth, json=payload)
                res.raise_for_status()
                return res.json(), res.status_code

        try:
            (res_json, status_code), retries = retry_with_backoff(_do_post, retries=3, base_delay=0.3)
            latency = int((time.time() - t0) * 1000)
            link_id = res_json.get("id")
            short_url = res_json.get("short_url")

            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="create_payment_link",
                status="success",
                status_code=status_code,
                event_id=link_id,
                workspace_id=workspace_id,
                payload_summary={"amount": amount, "currency": currency},
                response_summary={"link_id": link_id, "short_url": short_url},
                latency_ms=latency,
                retry_count=retries
            )
            return {
                "payment_id": link_id,
                "checkout_url": short_url,
                "amount": amount,
                "currency": currency.upper(),
                "status": "created",
                "raw": res_json
            }
        except Exception as exc:
            latency = int((time.time() - t0) * 1000)
            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="create_payment_link",
                status="error",
                status_code=502,
                workspace_id=workspace_id,
                payload_summary={"amount": amount, "currency": currency},
                error_message=str(exc),
                latency_ms=latency,
                retry_count=2
            )
            logger.error(f"Razorpay link error: {exc}")
            return {"status": "error", "detail": str(exc)}

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_id = payload.get("event_id") or payload.get("id") or f"rzp_evt_{int(time.time())}"
        event_type = payload.get("event")
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        link_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})

        amount_paise = payment_entity.get("amount") or link_entity.get("amount", 0)
        amount = amount_paise / 100.0
        currency = payment_entity.get("currency") or link_entity.get("currency", "INR")
        payment_id = payment_entity.get("id") or link_entity.get("id")
        notes = payment_entity.get("notes") or link_entity.get("notes", {})
        status = "paid" if event_type in ["payment.captured", "payment_link.paid"] else "pending"

        return {
            "event_id": str(event_id),
            "event_type": event_type,
            "payment_id": str(payment_id),
            "amount": float(amount),
            "currency": currency.upper(),
            "status": status,
            "metadata": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw": payload
        }

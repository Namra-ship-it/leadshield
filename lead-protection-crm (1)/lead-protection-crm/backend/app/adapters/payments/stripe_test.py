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

logger = logging.getLogger("adapters.stripe_test")

class StripeTestAdapter(PaymentAdapter):
    """
    Stripe Test Mode integration for Checkout Sessions and webhook signature validation.
    """
    @property
    def name(self) -> str:
        return "stripe_test"

    @property
    def is_mock(self) -> bool:
        return False

    def get_limits_note(self) -> str:
        return "Stripe Test Mode: 100 API requests/sec limit. Supports 4242 test cards. Instant sandbox webhooks without real fund transfers."

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        secret = settings.STRIPE_WEBHOOK_SECRET
        if not secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not configured; rejecting webhook")
            return False

        sig_header = headers.get("stripe-signature") or headers.get("Stripe-Signature")
        if not sig_header:
            return False

        try:
            parts = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = parts.get("t")
            v1_sig = parts.get("v1")
            if not timestamp or not v1_sig:
                return False

            signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
            expected_sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_sig, v1_sig)
        except Exception as e:
            logger.error(f"Stripe signature parse error: {e}")
            return False

    def create_payment_link(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        secret_key = settings.STRIPE_SECRET_KEY

        if not secret_key:
            latency = int((time.time() - t0) * 1000)
            err_msg = "STRIPE_SECRET_KEY not configured"
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

        url = "https://api.stripe.com/v1/checkout/sessions"
        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        unit_amount = int(amount * 100) if currency.lower() not in ["jpy", "krw"] else int(amount)
        form_data = {
            "mode": "payment",
            "success_url": "http://localhost:5173/payment-success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "http://localhost:5173/payment-cancelled",
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": str(unit_amount),
            "line_items[0][price_data][product_data][name]": description or "CRM Lead Guard Service"
        }
        if metadata:
            for k, v in metadata.items():
                form_data[f"metadata[{k}]"] = str(v)

        def _do_post():
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=headers, data=form_data)
                res.raise_for_status()
                return res.json(), res.status_code

        try:
            (res_json, status_code), retries = retry_with_backoff(_do_post, retries=3, base_delay=0.3)
            latency = int((time.time() - t0) * 1000)
            session_id = res_json.get("id")
            checkout_url = res_json.get("url")

            log_sync_call(
                provider_type=self.provider_type,
                provider_name=self.name,
                direction="outbound",
                action="create_payment_link",
                status="success",
                status_code=status_code,
                event_id=session_id,
                workspace_id=workspace_id,
                payload_summary={"amount": amount, "currency": currency, "description": description},
                response_summary={"session_id": session_id, "url": checkout_url},
                latency_ms=latency,
                retry_count=retries
            )
            return {
                "payment_id": session_id,
                "checkout_url": checkout_url,
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
            logger.error(f"Stripe checkout error: {exc}")
            return {"status": "error", "detail": str(exc)}

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_id = payload.get("id")
        event_type = payload.get("type")
        data_obj = payload.get("data", {}).get("object", {})

        amount_total = data_obj.get("amount_total")
        amount = (amount_total / 100.0) if amount_total else 0.0
        currency = data_obj.get("currency", "usd").upper()
        payment_id = data_obj.get("id")
        metadata = data_obj.get("metadata", {})
        status = "paid" if data_obj.get("payment_status") == "paid" or event_type == "payment_intent.succeeded" else "pending"

        return {
            "event_id": str(event_id),
            "event_type": event_type,
            "payment_id": str(payment_id),
            "amount": float(amount),
            "currency": currency,
            "status": status,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw": payload
        }

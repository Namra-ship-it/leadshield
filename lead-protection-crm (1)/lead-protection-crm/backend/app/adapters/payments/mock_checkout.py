import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.adapters.payments.base import PaymentAdapter
from app.adapters.base import log_sync_call

class MockCheckoutAdapter(PaymentAdapter):
    """
    Mock payment adapter for sandbox testing without external payment gateway accounts.
    Generates local mock checkout URLs and verifies mock webhooks.
    """
    @property
    def name(self) -> str:
        return "mock_checkout"

    @property
    def is_mock(self) -> bool:
        return True

    def get_limits_note(self) -> str:
        return "MOCK Checkout Engine: Zero fees. Simulates Stripe & Razorpay webhook flows locally for rapid UI and business logic testing."

    def create_payment_link(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        workspace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        payment_id = f"mock_pay_{uuid.uuid4().hex[:12]}"
        checkout_url = f"/mock-checkout/{payment_id}?amount={amount}&currency={currency}"

        res = {
            "payment_id": payment_id,
            "checkout_url": checkout_url,
            "amount": amount,
            "currency": currency.upper(),
            "description": description,
            "status": "created",
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type=self.provider_type,
            provider_name=self.name,
            direction="outbound",
            action="create_payment_link",
            status="success",
            status_code=200,
            event_id=payment_id,
            workspace_id=workspace_id,
            payload_summary={"amount": amount, "currency": currency, "description": description},
            response_summary={"payment_id": payment_id, "checkout_url": checkout_url},
            latency_ms=latency
        )
        return res

    def verify_webhook_signature(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        sig = headers.get("x-mock-signature") or headers.get("X-Mock-Signature")
        if sig == "invalid_sig":
            return False
        return True

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses simulated checkout completion payload:
        {
            "event_id": "mock_evt_123",
            "event_type": "checkout.session.completed",
            "payment_id": "mock_pay_123",
            "amount": 5000,
            "currency": "INR",
            "status": "paid",
            "metadata": { "lead_id": "...", "workspace_id": "..." }
        }
        """
        if not payload:
            return None

        event_id = payload.get("event_id") or f"mock_evt_{uuid.uuid4().hex[:10]}"
        event_type = payload.get("event_type") or "payment.succeeded"
        payment_id = payload.get("payment_id") or payload.get("id") or "mock_pay_unknown"
        amount = payload.get("amount", 0.0)
        currency = payload.get("currency", "USD")
        status = payload.get("status", "paid")
        metadata = payload.get("metadata", {})

        return {
            "event_id": str(event_id),
            "event_type": event_type,
            "payment_id": str(payment_id),
            "amount": float(amount),
            "currency": str(currency).upper(),
            "status": status,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw": payload
        }

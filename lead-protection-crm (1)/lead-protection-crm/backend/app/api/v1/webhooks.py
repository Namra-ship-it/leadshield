import time
import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Response, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.adapters.factory import (
    get_messaging_adapter,
    get_payment_adapter
)
from app.adapters.base import (
    log_sync_call,
    check_idempotency,
    mark_event_processed
)

logger = logging.getLogger("api.webhooks")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# ----------------- WhatsApp Webhooks ----------------- #

@router.get("/whatsapp")
async def verify_whatsapp_handshake(
    request: Request
):
    """
    Meta WhatsApp Cloud API webhook handshake verification.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    adapter = get_messaging_adapter()
    if hasattr(adapter, "verify_challenge"):
        verified_challenge = adapter.verify_challenge(mode, token, challenge)
        if verified_challenge:
            return Response(content=str(verified_challenge), media_type="text/plain", status_code=200)

    # Allow mock handshake test
    if token == "leadguard_wa_verify_token_2026":
        return Response(content=str(challenge or "verified"), media_type="text/plain", status_code=200)

    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Inbound WhatsApp message webhook (Meta Cloud API and Mock WhatsApp).
    Verifies HMAC signatures and deduplicates by event_id.
    """
    t0 = time.time()
    raw_body = await request.body()
    headers = dict(request.headers)
    adapter = get_messaging_adapter()

    # 1. Signature Verification
    if not adapter.verify_webhook_signature(headers, raw_body):
        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type="messaging",
            provider_name=adapter.name,
            direction="inbound",
            action="webhook_received",
            status="error",
            status_code=401,
            error_message="Invalid webhook signature",
            latency_ms=latency,
            db=db
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    # 2. Parse payload
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed JSON: {e}")

    parsed = adapter.parse_inbound_message(payload)
    if not parsed:
        # Acknowledge non-message status events (read receipts, delivery reports)
        return {"status": "ignored_non_message_event"}

    event_id = parsed.get("event_id")

    # 3. Idempotency Check
    cached = check_idempotency(db, adapter.name, event_id)
    if cached:
        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type="messaging",
            provider_name=adapter.name,
            direction="inbound",
            action="webhook_deduplicated",
            status="success",
            status_code=200,
            event_id=event_id,
            payload_summary={"sender": parsed.get("sender_phone"), "text": parsed.get("text")},
            response_summary={"deduplicated": True},
            latency_ms=latency,
            db=db
        )
        return {"status": "deduplicated", "event_id": event_id, "cached": cached}

    # 4. Normalize phone and match contact for inbound message
    from app.core.phone import normalize_phone_e164
    from app.data_access.contact_repo import contact_repo

    sender_raw = parsed.get("sender_phone")
    sender_norm = normalize_phone_e164(sender_raw) if sender_raw else None
    if sender_norm:
        parsed["sender_phone"] = sender_norm

    matched_contact = contact_repo.get_by_phone(db, sender_norm or sender_raw) if (sender_norm or sender_raw) else None

    response_data = {
        "status": "received",
        "event_id": event_id,
        "sender": sender_norm or sender_raw,
        "text": parsed.get("text")
    }
    if matched_contact:
        response_data["contact_id"] = matched_contact.id
        response_data["contact_name"] = matched_contact.full_name

    mark_event_processed(
        db=db,
        provider_name=adapter.name,
        event_id=event_id,
        event_type="inbound_message",
        response_data=response_data
    )

    latency = int((time.time() - t0) * 1000)
    log_sync_call(
        provider_type="messaging",
        provider_name=adapter.name,
        direction="inbound",
        action="webhook_received",
        status="success",
        status_code=200,
        event_id=event_id,
        payload_summary={"sender": parsed.get("sender_phone"), "text": parsed.get("text")},
        response_summary=response_data,
        latency_ms=latency,
        db=db
    )

    return response_data

# ----------------- Stripe Webhooks ----------------- #

@router.post("/stripe")
async def receive_stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Inbound Stripe payment webhook with Stripe-Signature HMAC validation and idempotency.
    """
    t0 = time.time()
    raw_body = await request.body()
    headers = dict(request.headers)
    adapter = get_payment_adapter("stripe_test")

    # 1. Signature Verification
    if not adapter.verify_webhook_signature(headers, raw_body):
        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type="payment",
            provider_name=adapter.name,
            direction="inbound",
            action="webhook_received",
            status="error",
            status_code=400,
            error_message="Invalid Stripe-Signature",
            latency_ms=latency,
            db=db
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe-Signature")

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed JSON: {e}")

    parsed = adapter.parse_webhook_event(payload)
    event_id = parsed.get("event_id") if parsed else payload.get("id")

    # 2. Idempotency Check
    cached = check_idempotency(db, adapter.name, event_id)
    if cached:
        return {"status": "deduplicated", "event_id": event_id}

    response_data = {
        "status": "processed",
        "event_id": event_id,
        "event_type": parsed.get("event_type") if parsed else payload.get("type"),
        "payment_id": parsed.get("payment_id") if parsed else None,
        "amount": parsed.get("amount") if parsed else 0
    }

    mark_event_processed(
        db=db,
        provider_name=adapter.name,
        event_id=event_id,
        event_type=response_data["event_type"],
        response_data=response_data
    )

    latency = int((time.time() - t0) * 1000)
    log_sync_call(
        provider_type="payment",
        provider_name=adapter.name,
        direction="inbound",
        action="webhook_received",
        status="success",
        status_code=200,
        event_id=event_id,
        payload_summary={"event_type": response_data["event_type"], "amount": response_data["amount"]},
        response_summary=response_data,
        latency_ms=latency,
        db=db
    )

    return response_data

# ----------------- Razorpay Webhooks ----------------- #

@router.post("/razorpay")
async def receive_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Inbound Razorpay payment webhook with X-Razorpay-Signature HMAC validation.
    """
    t0 = time.time()
    raw_body = await request.body()
    headers = dict(request.headers)
    adapter = get_payment_adapter("razorpay_test")

    # 1. Signature Verification
    if not adapter.verify_webhook_signature(headers, raw_body):
        latency = int((time.time() - t0) * 1000)
        log_sync_call(
            provider_type="payment",
            provider_name=adapter.name,
            direction="inbound",
            action="webhook_received",
            status="error",
            status_code=400,
            error_message="Invalid X-Razorpay-Signature",
            latency_ms=latency,
            db=db
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Razorpay-Signature")

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed JSON: {e}")

    parsed = adapter.parse_webhook_event(payload)
    event_id = parsed.get("event_id") if parsed else payload.get("id")

    cached = check_idempotency(db, adapter.name, event_id)
    if cached:
        return {"status": "deduplicated", "event_id": event_id}

    response_data = {
        "status": "processed",
        "event_id": event_id,
        "event_type": parsed.get("event_type") if parsed else payload.get("event"),
        "payment_id": parsed.get("payment_id") if parsed else None,
        "amount": parsed.get("amount") if parsed else 0
    }

    mark_event_processed(
        db=db,
        provider_name=adapter.name,
        event_id=event_id,
        event_type=response_data["event_type"],
        response_data=response_data
    )

    latency = int((time.time() - t0) * 1000)
    log_sync_call(
        provider_type="payment",
        provider_name=adapter.name,
        direction="inbound",
        action="webhook_received",
        status="success",
        status_code=200,
        event_id=event_id,
        payload_summary={"event_type": response_data["event_type"], "amount": response_data["amount"]},
        response_summary=response_data,
        latency_ms=latency,
        db=db
    )

    return response_data

# ----------------- Mock Payment Webhook ----------------- #

@router.post("/mock-payment")
async def receive_mock_payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Simulation endpoint for mock checkout triggers.
    """
    t0 = time.time()
    raw_body = await request.body()
    headers = dict(request.headers)
    adapter = get_payment_adapter("mock_checkout")

    if not adapter.verify_webhook_signature(headers, raw_body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Malformed JSON: {e}")

    parsed = adapter.parse_webhook_event(payload)
    event_id = parsed.get("event_id")

    cached = check_idempotency(db, adapter.name, event_id)
    if cached:
        return {"status": "deduplicated", "event_id": event_id}

    response_data = {
        "status": "processed",
        "event_id": event_id,
        "payment_id": parsed.get("payment_id"),
        "amount": parsed.get("amount")
    }

    mark_event_processed(
        db=db,
        provider_name=adapter.name,
        event_id=event_id,
        event_type="mock_payment_completed",
        response_data=response_data
    )

    latency = int((time.time() - t0) * 1000)
    log_sync_call(
        provider_type="payment",
        provider_name=adapter.name,
        direction="inbound",
        action="webhook_received",
        status="success",
        status_code=200,
        event_id=event_id,
        payload_summary=parsed,
        response_summary=response_data,
        latency_ms=latency,
        db=db
    )

    return response_data

import pytest
import hmac
import hashlib
from datetime import datetime, timezone
from app.adapters.factory import (
    get_messaging_adapter,
    get_payment_adapter,
    get_calendar_adapter,
    get_notify_adapter,
    get_all_adapters_status
)
from app.adapters.messaging import MockWhatsAppAdapter, MetaWhatsAppCloudAdapter, TelegramMessagingAdapter
from app.adapters.payments import MockCheckoutAdapter, StripeTestAdapter, RazorpayTestAdapter
from app.adapters.calendar import InternalIcsAdapter, GoogleOAuthCalendarAdapter
from app.adapters.notify import TelegramNotifyAdapter, SlackWebhookAdapter, SmtpEmailAdapter
from app.models.integration import SyncHistory, ProcessedEvent
from app.core.config import settings

def test_adapter_factory_and_mock_parity():
    """
    Test that factory provides adapters with identical interface contracts,
    correct types, and proper mock indicators.
    """
    # Messaging parity
    mock_wa = MockWhatsAppAdapter()
    meta_wa = MetaWhatsAppCloudAdapter()
    tg_msg = TelegramMessagingAdapter()

    for adapter in [mock_wa, meta_wa, tg_msg]:
        assert adapter.provider_type == "messaging"
        assert isinstance(adapter.get_limits_note(), str)
        assert len(adapter.get_limits_note()) > 10
        assert hasattr(adapter, "send_message")
        assert hasattr(adapter, "verify_webhook_signature")
        assert hasattr(adapter, "parse_inbound_message")

    assert mock_wa.is_mock is True
    assert meta_wa.is_mock is False
    assert tg_msg.is_mock is False

    # Payments parity
    mock_pay = MockCheckoutAdapter()
    stripe = StripeTestAdapter()
    razorpay = RazorpayTestAdapter()

    for adapter in [mock_pay, stripe, razorpay]:
        assert adapter.provider_type == "payment"
        assert hasattr(adapter, "create_payment_link")
        assert hasattr(adapter, "verify_webhook_signature")
        assert hasattr(adapter, "parse_webhook_event")

    assert mock_pay.is_mock is True
    assert stripe.is_mock is False
    assert razorpay.is_mock is False

    # Calendar parity
    ics = InternalIcsAdapter()
    gcal = GoogleOAuthCalendarAdapter()
    for adapter in [ics, gcal]:
        assert adapter.provider_type == "calendar"
        assert hasattr(adapter, "get_free_busy")
        assert hasattr(adapter, "create_event")
        assert hasattr(adapter, "export_ics")

    assert ics.is_mock is True
    assert gcal.is_mock is False

    # Notify parity
    tg_notify = TelegramNotifyAdapter()
    slack = SlackWebhookAdapter()
    smtp = SmtpEmailAdapter()
    for adapter in [tg_notify, slack, smtp]:
        assert adapter.provider_type == "notify"
        assert hasattr(adapter, "send_notification")
        assert adapter.is_mock is False

def test_internal_ics_calendar_and_overlap_blocking():
    """
    Test that the internal calendar adapter blocks overlapping appointments
    and generates valid RFC 5545 iCalendar content.
    """
    adapter = InternalIcsAdapter()
    from datetime import datetime, timedelta, timezone
    t1 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 20, 11, 0, 0, tzinfo=timezone.utc)

    # 1. First booking succeeds
    ev1 = adapter.create_event(
        title="Consultation Call",
        start_time=t1,
        end_time=t2,
        attendees=["client@example.com"],
        user_email_or_id="rep_123"
    )
    assert ev1.get("status") == "confirmed"
    assert "BEGIN:VCALENDAR" in ev1["ics_content"]
    assert "BEGIN:VEVENT" in ev1["ics_content"]
    assert "END:VCALENDAR" in ev1["ics_content"]

    # 2. Overlapping booking must be blocked
    t_overlap_start = datetime(2026, 10, 20, 10, 30, 0, tzinfo=timezone.utc)
    t_overlap_end = datetime(2026, 10, 20, 11, 30, 0, tzinfo=timezone.utc)
    ev_clash = adapter.create_event(
        title="Clashing Meeting",
        start_time=t_overlap_start,
        end_time=t_overlap_end,
        attendees=["other@example.com"],
        user_email_or_id="rep_123"
    )
    assert ev_clash.get("status") == "error"
    assert "overlap" in ev_clash.get("detail", "").lower()

def test_webhook_signature_rejection_and_idempotency(client, db_session):
    """
    Test webhook signature verification:
    - Rejects invalid signatures with 401/400
    - Accepts valid signatures
    - Deduplicates identical event IDs without re-processing
    """
    # 1. Invalid signature rejected
    bad_res = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"from": "+919876543210", "body": "Hello", "message_id": "test_evt_1"},
        headers={"X-Mock-Signature": "invalid_sig"}
    )
    assert bad_res.status_code == 401

    # 2. Valid webhook processed
    good_res = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"from": "+919876543210", "body": "Hello First Time", "message_id": "test_evt_100"}
    )
    assert good_res.status_code == 200
    assert good_res.json()["status"] == "received"
    assert good_res.json()["event_id"] == "test_evt_100"

    # 3. Duplicate webhook with same event_id is deduplicated
    dup_res = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"from": "+919876543210", "body": "Hello Second Time", "message_id": "test_evt_100"}
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["status"] == "deduplicated"

    # Verify sync_history records were created
    history = db_session.query(SyncHistory).filter(SyncHistory.event_id == "test_evt_100").all()
    assert len(history) >= 2

def test_integrations_status_and_sync_history_endpoints(client):
    """
    Test that authenticated users can query provider statuses (with MOCK flags,
    limits notes, and sync histories).
    """
    # Signup owner
    res_signup = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Adapter Tech Agency",
        "full_name": "Integration Admin",
        "email": "admin@adaptertech.com",
        "password": "Password123!"
    })
    token = res_signup.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Status endpoint
    res_status = client.get("/api/v1/integrations/status", headers=headers)
    assert res_status.status_code == 200
    status_data = res_status.json()

    assert "messaging" in status_data
    assert "payment" in status_data
    assert "calendar" in status_data
    assert "notify" in status_data

    assert status_data["messaging"]["is_mock"] is True  # default mock_whatsapp
    assert status_data["payment"]["is_mock"] is True    # default mock_checkout
    assert status_data["calendar"]["is_mock"] is True   # default internal_ics
    assert "limits_note" in status_data["messaging"]

    # 2. Test provider connection
    test_res = client.post("/api/v1/integrations/test/messaging", headers=headers)
    assert test_res.status_code == 200
    assert test_res.json()["status"] == "ok"

    # 3. Query sync history
    res_hist = client.get("/api/v1/integrations/sync-history", headers=headers)
    assert res_hist.status_code == 200
    assert res_hist.json()["total"] >= 1
    assert "items" in res_hist.json()

def test_telegram_adapter_not_configured_returns_400_and_records_sync_history(client, db_session):
    """
    Test 2: Telegram adapter:
    If token or chat_id is missing, return a clear 400 with the message,
    record it in sync history as 'not configured', and show is_configured False.
    """
    orig_token = settings.TELEGRAM_BOT_TOKEN
    orig_chat_id = settings.TELEGRAM_DEFAULT_CHAT_ID

    try:
        settings.TELEGRAM_BOT_TOKEN = None
        settings.TELEGRAM_DEFAULT_CHAT_ID = None

        tg_notify = TelegramNotifyAdapter()
        tg_msg = TelegramMessagingAdapter()

        # Both adapters must report is_configured == False
        assert tg_notify.is_configured is False
        assert tg_msg.is_configured is False

        # Status check includes is_configured False
        status_info = tg_notify.get_status(db_session)
        assert status_info["is_configured"] is False

        # Direct send_notification returns clear 400 and records in sync history
        res_notify = tg_notify.send_notification(
            title="Urgent Alert",
            message="Test message",
            workspace_id="ws_test"
        )
        assert res_notify["status"] == "error"
        assert res_notify["status_code"] == 400
        assert "not configured" in res_notify["detail"].lower()

        # Direct send_message returns clear 400 and records in sync history
        res_msg = tg_msg.send_message(
            to="+15551234567",
            text="Test telegram",
            workspace_id="ws_test"
        )
        assert res_msg["status"] == "error"
        assert res_msg["status_code"] == 400
        assert "not configured" in res_msg["detail"].lower()

        # Verify sync_history audit log entries
        sync_records = db_session.query(SyncHistory).filter(
            SyncHistory.provider_name == "telegram",
            SyncHistory.error_message == "not configured"
        ).all()
        assert len(sync_records) >= 2
        for r in sync_records:
            assert r.status == "error"
            assert r.status_code == 400
            assert r.error_message == "not configured"

        # Signup user and test endpoint with telegram as notify provider
        res_signup = client.post("/api/v1/auth/signup", json={
            "workspace_name": "Telegram Test Agency",
            "full_name": "Telegram Tester",
            "email": "tester@telegramagency.com",
            "password": "Password123!"
        })
        headers = {"Authorization": f"Bearer {res_signup.json()['access_token']}"}

        # Testing notify endpoint with unconfigured telegram returns 400
        test_res = client.post("/api/v1/integrations/test/notify", headers=headers)
        assert test_res.status_code == 400
        assert "not configured" in test_res.json()["detail"].lower()

    finally:
        settings.TELEGRAM_BOT_TOKEN = orig_token
        settings.TELEGRAM_DEFAULT_CHAT_ID = orig_chat_id

def test_calendar_test_connection_repeated_read_only_checks_never_409(client):
    """
    Test 3: Calendar Test Connection:
    Perform a read-only free/busy check instead of booking a fixed slot,
    so repeated tests never return 409.
    """
    res_signup = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Calendar Check Agency",
        "full_name": "Calendar Admin",
        "email": "calendar@check.com",
        "password": "Password123!"
    })
    headers = {"Authorization": f"Bearer {res_signup.json()['access_token']}"}

    # Repeated tests (5 times in a row) must all succeed with 200 and never 409
    for _ in range(5):
        res = client.post("/api/v1/integrations/test/calendar", headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "ok"
        assert data["result"]["read_only_check"] is True
        assert "busy_slots" in data["result"]

def test_health_endpoints(client):
    """
    Test 4: Add GET /health endpoint.
    """
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert "app" in res.json()

    # Also test /api/health and /api/v1/health
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200

def test_phone_normalization_on_save_and_matching(client, db_session):
    """
    Test 5: Normalize all phone numbers to E.164 on save and when matching incoming messages.
    """
    res_signup = client.post("/api/v1/auth/signup", json={
        "workspace_name": "Phone Norm Agency",
        "full_name": "Phone Admin",
        "email": "admin@phonenorm.com",
        "password": "Password123!"
    })
    headers = {"Authorization": f"Bearer {res_signup.json()['access_token']}"}

    # 1. Contact with formatted US phone -> normalized to +14155552671 on save
    c1_res = client.post("/api/v1/contacts", headers=headers, json={
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+1 (415) 555-2671"
    })
    assert c1_res.status_code == 201
    assert c1_res.json()["phone"] == "+14155552671"

    # 2. Contact with 10-digit Indian phone with dashes -> normalized to +919876543210
    c2_res = client.post("/api/v1/contacts", headers=headers, json={
        "full_name": "Rajesh Kumar",
        "phone": "98765-43210"
    })
    assert c2_res.status_code == 201
    assert c2_res.json()["phone"] == "+919876543210"

    # 3. User with formatted phone -> normalized on save
    u_res = client.post("/api/v1/users", headers=headers, json={
        "email": "rep@phonenorm.com",
        "full_name": "Rep User",
        "password": "Password123!",
        "role": "user",
        "phone": "(415) 555-9999"
    })
    assert u_res.status_code == 201
    assert u_res.json()["phone"] == "+14155559999"

    # 4. Incoming message webhook with raw/unformatted phone matches contact saved in E.164
    wa_res = client.post(
        "/api/v1/webhooks/whatsapp",
        json={
            "from": "415-555-2671",  # Unformatted sender
            "body": "Hi, I need follow up on my inquiry",
            "message_id": "msg_norm_101"
        }
    )
    assert wa_res.status_code == 200
    wa_data = wa_res.json()
    assert wa_data["sender"] == "+14155552671"  # Normalized to E.164
    assert wa_data.get("contact_id") == c1_res.json()["id"]  # Successfully matched to contact!
    assert wa_data.get("contact_name") == "John Doe"

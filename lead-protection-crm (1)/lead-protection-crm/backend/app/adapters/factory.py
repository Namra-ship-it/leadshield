import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.adapters.messaging import (
    MessagingAdapter,
    MockWhatsAppAdapter,
    MetaWhatsAppCloudAdapter,
    TelegramMessagingAdapter
)
from app.adapters.payments import (
    PaymentAdapter,
    MockCheckoutAdapter,
    StripeTestAdapter,
    RazorpayTestAdapter
)
from app.adapters.calendar import (
    CalendarAdapter,
    InternalIcsAdapter,
    GoogleOAuthCalendarAdapter
)
from app.adapters.notify import (
    NotifyAdapter,
    TelegramNotifyAdapter,
    SlackWebhookAdapter,
    SmtpEmailAdapter
)

logger = logging.getLogger("adapters.factory")

# Cached instances
_messaging_instances: Dict[str, MessagingAdapter] = {}
_payment_instances: Dict[str, PaymentAdapter] = {}
_calendar_instances: Dict[str, CalendarAdapter] = {}
_notify_instances: Dict[str, NotifyAdapter] = {}

def get_messaging_adapter(provider_name: Optional[str] = None) -> MessagingAdapter:
    name = (provider_name or settings.MESSAGING_PROVIDER or "mock_whatsapp").lower()
    if name not in _messaging_instances:
        if name == "meta_whatsapp_cloud":
            _messaging_instances[name] = MetaWhatsAppCloudAdapter()
        elif name == "telegram":
            _messaging_instances[name] = TelegramMessagingAdapter()
        else:
            _messaging_instances[name] = MockWhatsAppAdapter()
    return _messaging_instances[name]

def get_payment_adapter(provider_name: Optional[str] = None) -> PaymentAdapter:
    name = (provider_name or settings.PAYMENT_PROVIDER or "mock_checkout").lower()
    if name not in _payment_instances:
        if name == "stripe_test":
            _payment_instances[name] = StripeTestAdapter()
        elif name == "razorpay_test":
            _payment_instances[name] = RazorpayTestAdapter()
        else:
            _payment_instances[name] = MockCheckoutAdapter()
    return _payment_instances[name]

def get_calendar_adapter(provider_name: Optional[str] = None) -> CalendarAdapter:
    name = (provider_name or settings.CALENDAR_PROVIDER or "internal_ics").lower()
    if name not in _calendar_instances:
        if name == "google_oauth":
            _calendar_instances[name] = GoogleOAuthCalendarAdapter()
        else:
            _calendar_instances[name] = InternalIcsAdapter()
    return _calendar_instances[name]

def get_notify_adapter(provider_name: Optional[str] = None) -> NotifyAdapter:
    name = (provider_name or settings.NOTIFY_PROVIDER or "telegram").lower()
    if name not in _notify_instances:
        if name == "slack_webhook":
            _notify_instances[name] = SlackWebhookAdapter()
        elif name == "smtp_email":
            _notify_instances[name] = SmtpEmailAdapter()
        else:
            _notify_instances[name] = TelegramNotifyAdapter()
    return _notify_instances[name]

def get_all_adapters_status(db: Session, workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns full status overview of all 4 active integration providers:
    - active provider name
    - is_mock badge status
    - limits note
    - last success timestamp
    - last error timestamp & message
    - total calls & success rate
    - list of all supported options
    """
    messaging = get_messaging_adapter()
    payment = get_payment_adapter()
    calendar = get_calendar_adapter()
    notify = get_notify_adapter()

    return {
        "messaging": {
            **messaging.get_status(db, workspace_id),
            "available_options": ["mock_whatsapp", "meta_whatsapp_cloud", "telegram"],
            "configured_in_env": settings.MESSAGING_PROVIDER
        },
        "payment": {
            **payment.get_status(db, workspace_id),
            "available_options": ["mock_checkout", "stripe_test", "razorpay_test"],
            "configured_in_env": settings.PAYMENT_PROVIDER
        },
        "calendar": {
            **calendar.get_status(db, workspace_id),
            "available_options": ["internal_ics", "google_oauth"],
            "configured_in_env": settings.CALENDAR_PROVIDER
        },
        "notify": {
            **notify.get_status(db, workspace_id),
            "available_options": ["telegram", "slack_webhook", "smtp_email"],
            "configured_in_env": settings.NOTIFY_PROVIDER
        }
    }

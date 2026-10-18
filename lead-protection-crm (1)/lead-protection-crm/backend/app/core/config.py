import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Protection CRM"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-lead-protection-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./lead_crm.db")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Active Provider Adapters (chosen via env vars)
    MESSAGING_PROVIDER: str = os.getenv("MESSAGING_PROVIDER", "mock_whatsapp")  # meta_whatsapp_cloud, telegram, mock_whatsapp
    PAYMENT_PROVIDER: str = os.getenv("PAYMENT_PROVIDER", "mock_checkout")       # stripe_test, razorpay_test, mock_checkout
    CALENDAR_PROVIDER: str = os.getenv("CALENDAR_PROVIDER", "internal_ics")      # google_oauth, internal_ics
    NOTIFY_PROVIDER: str = os.getenv("NOTIFY_PROVIDER", "telegram")              # telegram, slack_webhook, smtp_email

    # Meta WhatsApp Cloud API credentials
    META_WA_PHONE_NUMBER_ID: Optional[str] = os.getenv("META_WA_PHONE_NUMBER_ID", None)
    META_WA_ACCESS_TOKEN: Optional[str] = os.getenv("META_WA_ACCESS_TOKEN", None)
    META_WA_APP_SECRET: Optional[str] = os.getenv("META_WA_APP_SECRET", None)
    META_WA_VERIFY_TOKEN: str = os.getenv("META_WA_VERIFY_TOKEN", "leadguard_wa_verify_token_2026")

    # Twilio legacy compatibility
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID", None)
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN", None)
    TWILIO_WHATSAPP_NUMBER: Optional[str] = os.getenv("TWILIO_WHATSAPP_NUMBER", None)

    # Stripe Test Mode credentials
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY", None)
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET", None)
    STRIPE_PUBLIC_KEY: Optional[str] = os.getenv("STRIPE_PUBLIC_KEY", None)

    # Razorpay Test Mode credentials
    RAZORPAY_KEY_ID: Optional[str] = os.getenv("RAZORPAY_KEY_ID", None)
    RAZORPAY_KEY_SECRET: Optional[str] = os.getenv("RAZORPAY_KEY_SECRET", None)
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = os.getenv("RAZORPAY_WEBHOOK_SECRET", None)

    # Google Calendar OAuth credentials
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID", None)
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET", None)
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/calendar/google/callback")

    # Slack Incoming Webhook
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL", None)

    # SMTP Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", None)
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "alerts@leadguardcrm.com")

    # Telegram Escalation & Team Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", None)
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_SECRET", "leadguard_telegram_secret_2026")
    TELEGRAM_DEFAULT_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_DEFAULT_CHAT_ID", None)

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()

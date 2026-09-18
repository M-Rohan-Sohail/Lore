from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/lore"
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_JWT_SECRET: str = "changeme"
    AI_PROVIDER_KEYS: str = "{}"
    REDIS_URL: str = ""
    CRON_SECRET: str = "changeme"
    SENTRY_DSN: str = ""
    POSTHOG_KEY: str = ""
    CHROME_EXECUTABLE_PATH: str = "/usr/bin/google-chrome"
    
    # Notifications
    FCM_SERVICE_ACCOUNT_JSON: str = ""
    APNS_KEY: str = ""
    APNS_KEY_ID: str = ""
    APNS_TEAM_ID: str = ""
    APNS_TOPIC: str = ""
    APNS_USE_SANDBOX: bool = False
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "narrator@lore.app"
    
    # Billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""
    BILLING_CHECKOUT_SUCCESS_URL: str = "https://lore.app/billing/success"
    BILLING_CHECKOUT_CANCEL_URL: str = "https://lore.app/billing/cancel"

    @property
    def ai_provider_keys_parsed(self) -> dict[str, str]:
        if not self.AI_PROVIDER_KEYS:
            return {}
        try:
            return json.loads(self.AI_PROVIDER_KEYS)
        except json.JSONDecodeError:
            return {}

settings = Settings()

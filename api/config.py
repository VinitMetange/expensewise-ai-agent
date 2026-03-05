"""
ExpenseWise - App Configuration
All settings loaded from environment variables via pydantic-settings
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from .env file"""

    # --- App ---
    app_env: str = Field(default="development", env="APP_ENV")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=True, env="DEBUG")
    secret_key: str = Field(default="change-me", env="SECRET_KEY")

    # --- AWS ---
    aws_region: str = Field(default="ap-south-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")

    # --- Bedrock (Claude) ---
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        env="BEDROCK_MODEL_ID"
    )
    bedrock_max_tokens: int = Field(default=4096, env="BEDROCK_MAX_TOKENS")
    bedrock_temperature: float = Field(default=0.1, env="BEDROCK_TEMPERATURE")

    # --- Twilio / WhatsApp ---
    twilio_account_sid: Optional[str] = Field(None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, env="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(
        default="whatsapp:+14155238886", env="TWILIO_WHATSAPP_FROM"
    )
    whatsapp_webhook_secret: Optional[str] = Field(None, env="WHATSAPP_WEBHOOK_SECRET")

    # --- Google OAuth ---
    google_client_id: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        env="GOOGLE_REDIRECT_URI"
    )

    # --- Dropbox ---
    dropbox_app_key: Optional[str] = Field(None, env="DROPBOX_APP_KEY")
    dropbox_app_secret: Optional[str] = Field(None, env="DROPBOX_APP_SECRET")
    dropbox_redirect_uri: str = Field(
        default="http://localhost:8000/auth/dropbox/callback",
        env="DROPBOX_REDIRECT_URI"
    )

    # --- OneDrive ---
    microsoft_client_id: Optional[str] = Field(None, env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(None, env="MICROSOFT_CLIENT_SECRET")

    # --- Database ---
    database_url: str = Field(
        default="postgresql://expensewise_user:password@localhost:5432/expensewise_db",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # --- LangSmith ---
    langchain_tracing_v2: bool = Field(default=False, env="LANGCHAIN_TRACING_V2")
    langchain_api_key: Optional[str] = Field(None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="expensewise", env="LANGCHAIN_PROJECT")

    # --- Scheduler ---
    daily_summary_hour: int = Field(default=20, env="DAILY_SUMMARY_HOUR")
    daily_summary_minute: int = Field(default=0, env="DAILY_SUMMARY_MINUTE")
    timezone: str = Field(default="Asia/Kolkata", env="TIMEZONE")

    # --- Defaults ---
    default_currency: str = Field(default="INR", env="DEFAULT_CURRENCY")
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance - call this to get settings anywhere in the app"""
    return Settings()


# Convenience alias
settings = get_settings()

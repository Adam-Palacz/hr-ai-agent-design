"""Application configuration and settings management."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # LLM + embeddings provider (shared):
    # azure  – recommended for production (EU data residency via Azure region)
    # openai – convenient for local/dev/test (api.openai.com)
    llm_provider: str = "azure"

    # Azure OpenAI Configuration (single source of truth for models)
    # This is the default and currently most supported provider.
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: str = "https://openai-agentai-pl.openai.azure.com/"
    azure_openai_api_version: str = "2024-12-01-preview"
    # IMPORTANT: these names MUST match deployment names in Azure
    azure_openai_gpt_deployment: str = "gpt-5-mini"
    azure_openai_vision_deployment: str = "gpt-5-nano"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # Alias for the current text model „bieżący model tekstowy” – usually points
    # to the Azure deployment; can also be used as a logical model name for
    # other providers (e.g. OpenAI) when LLM_PROVIDER=openai.
    openai_model: str = "gpt-5-nano"
    openai_vision_model: str = "gpt-5-nano"

    # Temperature / timeout configuration shared by all agents
    openai_temperature: float = 1.0
    openai_feedback_temperature: float = 0.7
    openai_timeout: int = 600
    openai_max_retries: int = 2

    # OCR Configuration
    use_ocr: bool = False
    ocr_timeout: int = 600

    # PDF / CV processing
    max_text_length: int = 15000
    pdf_min_text_threshold: int = 100
    # When false, skip PDF read and LLM — feedback uses candidate record from DB only
    cv_parsing_enabled: bool = True
    # When false (and cv_parsing_enabled=true), read PDF text but skip LLM structured parse
    cv_llm_parsing_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    # Email/SMTP Configuration
    email_username: Optional[str] = None  # Email username (for Gmail, Zoho, etc.)
    email_password: Optional[str] = None  # Email password or app password
    smtp_host: str = (
        "smtp.zoho.eu"  # Default to Zoho EU, can be changed to smtp.zoho.com or smtp.gmail.com
    )
    smtp_port: int = 587  # 587 for TLS, 465 for SSL
    smtp_use_tls: bool = True  # Use TLS (True for port 587, False for port 465 with SSL)

    # IMAP Configuration (for email monitoring)
    imap_host: str = (
        "imap.zoho.eu"  # Default to Zoho EU, can be changed to imap.zoho.com or imap.gmail.com
    )
    imap_port: int = 993  # 993 for SSL

    # Email routing configuration
    iod_email: Optional[str] = None
    hr_email: Optional[str] = None
    email_check_interval: int = 60  # seconds
    email_monitor_enabled: bool = False

    # Privacy policy and information clause
    privacy_policy_url: Optional[str] = None  # URL to privacy policy / information clause
    company_website: Optional[str] = None  # Company website URL (optional)

    # Backward compatibility aliases (deprecated, use email_username/email_password)
    @property
    def gmail_username(self) -> Optional[str]:
        """Backward compatibility: returns email_username."""
        return self.email_username

    @property
    def gmail_password(self) -> Optional[str]:
        """Backward compatibility: returns email_password."""
        return self.email_password

    # OpenAI official (api.openai.com) configuration – used when llm_provider="openai"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_chat_model: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"

    @property
    def uses_openai_provider(self) -> bool:
        """True when chat and embeddings use the official OpenAI API."""
        return self.llm_provider.lower() == "openai"

    @property
    def api_key(self) -> str:
        """
        API key used by legacy call sites (agents, email classifier).

        When ``LLM_PROVIDER=openai``, returns ``OPENAI_API_KEY``; otherwise Azure.
        """
        if self.llm_provider.lower() == "openai":
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found. "
                    "Add it to the .env file or environment variables."
                )
            return self.openai_api_key
        if not self.azure_openai_api_key:
            raise ValueError(
                "AZURE_OPENAI_API_KEY not found. "
                "Add it to the .env file or environment variables."
            )
        return self.azure_openai_api_key

    @property
    def is_azure_configured(self) -> bool:
        """Check if Azure OpenAI is configured."""
        return bool(self.azure_openai_api_key and self.azure_openai_endpoint)

    def model_post_init(self, __context) -> None:
        """
        Provider-specific defaults after settings load.

        ``LLM_PROVIDER`` is authoritative: Azure env vars and deployment aliases are
        applied only when provider is Azure, so leftover Azure keys in ``.env`` do not
        affect OpenAI mode.
        """
        if self.uses_openai_provider:
            if self.openai_chat_model:
                self.openai_model = self.openai_chat_model
            return

        if self.azure_openai_api_key and self.azure_openai_endpoint:
            os.environ["OPENAI_API_KEY"] = self.azure_openai_api_key
            os.environ["OPENAI_API_BASE"] = self.azure_openai_endpoint
            os.environ["OPENAI_API_TYPE"] = "azure"
            os.environ["OPENAI_API_VERSION"] = self.azure_openai_api_version

            if self.azure_openai_gpt_deployment:
                self.openai_model = self.azure_openai_gpt_deployment
            if self.azure_openai_vision_deployment:
                self.openai_vision_model = self.azure_openai_vision_deployment


# Global settings instance
settings = Settings()

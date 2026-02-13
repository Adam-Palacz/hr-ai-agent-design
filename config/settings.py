"""Application configuration and settings management."""
import os
from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Azure OpenAI Configuration (single source of truth for models)
    # This is the *only* actively used API – classic OpenAI is disabled.
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: str = "https://openai-agentai-pl.openai.azure.com/"
    azure_openai_api_version: str = "2024-12-01-preview"
    # IMPORTANT: these names MUST match deployment names in Azure
    azure_openai_gpt_deployment: str = "gpt-4.1"
    azure_openai_vision_deployment: str = "gpt-5-nano"

    # Alias for the current text model „bieżący model tekstowy” – always points to Azure deployment
    # Set in model_post_init to azure_openai_gpt_deployment
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
    
    # PDF Processing
    max_text_length: int = 15000
    pdf_min_text_threshold: int = 100
    
    # Logging
    log_level: str = "INFO"
    verbose: bool = False
    
    # Email/SMTP Configuration
    email_username: Optional[str] = None  # Email username (for Gmail, Zoho, etc.)
    email_password: Optional[str] = None  # Email password or app password
    smtp_host: str = "smtp.zoho.eu"  # Default to Zoho EU, can be changed to smtp.zoho.com or smtp.gmail.com
    smtp_port: int = 587  # 587 for TLS, 465 for SSL
    smtp_use_tls: bool = True  # Use TLS (True for port 587, False for port 465 with SSL)
    
    # IMAP Configuration (for email monitoring)
    imap_host: str = "imap.zoho.eu"  # Default to Zoho EU, can be changed to imap.zoho.com or imap.gmail.com
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
    
    @property
    def api_key(self) -> str:
        """
        Returns the API key for Azure OpenAI.
        
        Classic OPENAI_API_KEY is no longer used – everything goes through Azure.
        """
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
        Additional initialization after settings are loaded.
        
        If Azure OpenAI is configured (endpoint + api_key), we set:
        - environment variables expected by the OpenAI client (Azure mode),
        - openai_model to the Azure deployment name (azure_openai_gpt_deployment).
        This way agents still use the single field settings.openai_model,
        but actually refer to the Azure deployment.
        """
        if self.azure_openai_api_key and self.azure_openai_endpoint:
            # Configure Azure mode for the OpenAI library
            os.environ["OPENAI_API_KEY"] = self.azure_openai_api_key
            # Use endpoint from Azure portal (e.g. https://xxx.openai.azure.com)
            os.environ["OPENAI_API_BASE"] = self.azure_openai_endpoint
            os.environ["OPENAI_API_TYPE"] = "azure"
            os.environ["OPENAI_API_VERSION"] = self.azure_openai_api_version
            
            # If deployment name is defined – use it as the model
            if self.azure_openai_gpt_deployment:
                self.openai_model = self.azure_openai_gpt_deployment
            if self.azure_openai_vision_deployment:
                self.openai_vision_model = self.azure_openai_vision_deployment


# Global settings instance
settings = Settings()


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
    
    # OpenAI API Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_vision_model: str = "gpt-4o"
    openai_temperature: float = 0.0
    openai_feedback_temperature: float = 0.7
    openai_timeout: int = 120
    openai_max_retries: int = 2
    
    # OCR Configuration
    use_ocr: bool = True
    ocr_timeout: int = 180
    
    # PDF Processing
    max_text_length: int = 15000
    pdf_min_text_threshold: int = 100
    
    # Logging
    log_level: str = "INFO"
    verbose: bool = False
    
    @property
    def api_key(self) -> str:
        """Get OpenAI API key, raise error if not set."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. "
                "Set it in .env file or environment variable."
            )
        return self.openai_api_key


# Global settings instance
settings = Settings()


"""Tests for configuration and settings."""

import pytest
from unittest.mock import patch

from config.settings import settings


def test_settings_has_expected_attributes():
    """Settings should have expected configuration attributes."""
    assert hasattr(settings, "azure_openai_api_key")
    assert hasattr(settings, "azure_openai_endpoint")
    assert hasattr(settings, "email_username")
    assert hasattr(settings, "smtp_host")
    assert hasattr(settings, "imap_host")
    assert hasattr(settings, "cv_parsing_enabled")
    assert hasattr(settings, "cv_llm_parsing_enabled")


def test_settings_smtp_imap_are_strings():
    """SMTP/IMAP host and port should be valid types (string and int)."""
    assert isinstance(settings.smtp_host, str)
    assert isinstance(settings.imap_host, str)
    assert isinstance(settings.smtp_port, int)
    assert settings.smtp_port > 0


def test_settings_deprecated_aliases():
    """Deprecated gmail_username/gmail_password should match email_username/email_password."""
    assert settings.gmail_username == settings.email_username
    assert settings.gmail_password == settings.email_password


def test_settings_api_key_returns_str():
    """api_key property should return non-empty string when AZURE_OPENAI_API_KEY is set."""
    key = settings.api_key
    assert isinstance(key, str)
    assert len(key) > 0


def test_settings_is_azure_configured():
    """is_azure_configured should be True when endpoint and key are set."""
    assert settings.is_azure_configured is True


def test_settings_api_key_raises_when_missing():
    """api_key property raises ValueError when AZURE_OPENAI_API_KEY is not set."""
    with patch.object(settings, "llm_provider", "azure"):
        with patch.object(settings, "azure_openai_api_key", None):
            with pytest.raises(ValueError) as exc_info:
                _ = settings.api_key
            assert "AZURE_OPENAI_API_KEY" in str(exc_info.value)


def test_settings_api_key_openai_provider():
    """api_key returns OPENAI_API_KEY when LLM_PROVIDER=openai."""
    with patch.object(settings, "llm_provider", "openai"):
        with patch.object(settings, "openai_api_key", "sk-test-openai"):
            assert settings.api_key == "sk-test-openai"


def test_settings_api_key_openai_raises_when_missing():
    """api_key raises when LLM_PROVIDER=openai but OPENAI_API_KEY is missing."""
    with patch.object(settings, "llm_provider", "openai"):
        with patch.object(settings, "openai_api_key", None):
            with pytest.raises(ValueError) as exc_info:
                _ = settings.api_key
            assert "OPENAI_API_KEY" in str(exc_info.value)


def test_model_post_init_openai_ignores_azure_keys(monkeypatch):
    """With LLM_PROVIDER=openai, Azure keys must not overwrite env or model names."""
    import os
    from config.settings import Settings

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "azure-should-not-win")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-deployment-from-azure")

    s = Settings()
    assert s.openai_model == "gpt-4o-mini"
    assert os.environ.get("OPENAI_API_KEY") == "sk-openai-test"

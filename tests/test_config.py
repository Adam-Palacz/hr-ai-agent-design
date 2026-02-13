"""Tests for configuration and settings."""

from config.settings import settings


def test_settings_has_expected_attributes():
    """Settings should have expected configuration attributes."""
    assert hasattr(settings, "azure_openai_api_key")
    assert hasattr(settings, "azure_openai_endpoint")
    assert hasattr(settings, "email_username")
    assert hasattr(settings, "smtp_host")
    assert hasattr(settings, "imap_host")

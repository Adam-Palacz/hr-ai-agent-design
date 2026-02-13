"""Tests for email_sender service (no real SMTP)."""

from unittest.mock import patch


def test_send_email_gmail_returns_false_when_no_credentials():
    """When EMAIL_USERNAME or EMAIL_PASSWORD are not set, send_email_gmail returns (False, None)."""
    with patch("services.email_sender.settings") as mock_settings:
        mock_settings.email_username = None
        mock_settings.email_password = None
        from services.email_sender import send_email_gmail

        success, message_id = send_email_gmail("test@example.com", "Subject", "<p>Body</p>")
        assert success is False
        assert message_id is None

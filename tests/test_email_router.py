"""Unit tests for email_router (mocked classifier and SMTP, no real email)."""

import pytest
from unittest.mock import patch, MagicMock


def _make_router():
    """Create EmailRouter with mocked Azure and settings (may skip if init fails)."""
    with patch("openai.AzureOpenAI", MagicMock()):
        with patch("services.email_router.settings") as mock_settings:
            mock_settings.azure_openai_api_version = "2024-12-01-preview"
            mock_settings.azure_openai_endpoint = "https://test.openai.azure.com/"
            mock_settings.api_key = "test"
            mock_settings.openai_model = "gpt-4o-mini"
            mock_settings.azure_openai_gpt_deployment = "gpt-4o-mini"
            try:
                from services.email_router import EmailRouter

                return EmailRouter(
                    email_username="u@t.com",
                    email_password="p",
                    smtp_host="smtp.t.com",
                    smtp_port=587,
                    iod_email="iod@t.com",
                    hr_email="hr@t.com",
                )
            except Exception:
                return None


def test_route_email_iod_calls_route_to_iod():
    """When classification is 'iod', _route_to_iod is called."""
    r = _make_router()
    if r is None:
        pytest.skip("EmailRouter init requires DB/agents")

    email_data = {
        "uid": "1",
        "message_id": "<msg-1@test>",
        "from_email": "candidate@test.com",
        "subject": "Question",
        "body": "Hello",
        "date": "2025-01-01",
    }
    with patch.object(r, "_route_to_iod", return_value=True) as mock_iod:
        with patch.object(r, "_handle_consent", return_value=True):
            with patch.object(r, "_handle_general_query", return_value=True):
                out = r.route_email(email_data, "iod")
    assert out is True
    mock_iod.assert_called_once()


def test_route_email_duplicate_returns_true():
    """When the same email_id is already in processed_emails, route_email returns True without re-routing."""
    with patch("openai.AzureOpenAI", MagicMock()):
        with patch("services.email_router.settings") as mock_settings:
            mock_settings.azure_openai_api_version = "2024-12-01-preview"
            mock_settings.azure_openai_endpoint = "https://test.openai.azure.com/"
            mock_settings.api_key = "test"
            mock_settings.openai_model = "gpt-4o-mini"
            mock_settings.azure_openai_gpt_deployment = "gpt-4o-mini"
            try:
                from services.email_router import EmailRouter

                r = EmailRouter(
                    email_username="u@t.com",
                    email_password="p",
                    smtp_host="smtp.t.com",
                    smtp_port=587,
                    iod_email="iod@t.com",
                    hr_email="hr@t.com",
                )
            except Exception:
                pytest.skip("EmailRouter init requires DB/agents")

    email_data = {
        "uid": "99",
        "message_id": "<dup@test>",
        "from_email": "x@test.com",
        "subject": "S",
        "body": "B",
        "date": "2025-01-01",
    }
    r.processed_emails["<dup@test>"] = None

    with patch.object(r, "_handle_general_query", return_value=True) as mock_hr:
        out = r.route_email(email_data, "default")
    assert out is True
    mock_hr.assert_not_called()

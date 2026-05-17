"""Unit tests for email_router (mocked classifier and SMTP, no real email)."""

import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace


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


def test_route_email_consent_classes_call_handle_consent():
    """When classification is consent_yes/no, _handle_consent is called."""
    r = _make_router()
    if r is None:
        pytest.skip("EmailRouter init requires DB/agents")

    for classification in ("consent_yes", "consent_no"):
        r.processed_emails.clear()
        email_data = {
            "uid": classification,
            "message_id": f"<{classification}@test>",
            "from_email": "candidate@test.com",
            "subject": "Re: feedback",
            "body": "zgoda",
            "date": "2025-01-01",
        }
        with patch.object(r, "_handle_consent", return_value=True) as mock_consent:
            out = r.route_email(email_data, classification)

        assert out is True
        mock_consent.assert_called_once_with(email_data, classification)


def test_handle_consent_no_updates_candidate_flag_false():
    r = _make_router()
    if r is None:
        pytest.skip("EmailRouter init requires DB/agents")

    candidate = SimpleNamespace(id=11, first_name="Adam", last_name="Palacz", email="adam@test.com")

    with (
        patch("services.email_router.get_feedback_email_by_message_id", return_value=None),
        patch("services.email_router.get_candidate_by_email", return_value=candidate),
        patch("services.email_router.update_candidate") as mock_update,
        patch.object(r, "_send_email", return_value=True),
    ):
        out = r._handle_consent(
            {
                "from_email": "adam@test.com",
                "subject": "Re: Odpowiedź na aplikację",
                "body": "Nie chce brac udzialu w dalszych rekrutacjach",
            },
            "consent_no",
        )

    assert out is True
    mock_update.assert_called_once_with(11, consent_for_other_positions=False)


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


def test_handle_general_query_direct_answer_sends_response():
    r = _make_router()
    if r is None:
        pytest.skip("EmailRouter init requires DB/agents")

    r.query_classifier = MagicMock()
    r.query_classifier.classify_query.return_value = {
        "action": "direct_answer",
        "confidence": 0.9,
        "reasoning": "basic knowledge",
    }
    r.query_responder = MagicMock()
    r.query_responder.generate_response.return_value = "Odpowiedź\n\nZ wyrazami szacunku\n\nDział HR"

    email_data = {"from_email": "candidate@test.com", "subject": "Etapy", "body": "Ile etapów?"}
    with (
        patch.object(r, "_send_email", return_value=True) as mock_send,
        patch.object(r, "_notify_hr_about_auto_response") as mock_notify,
        patch.object(r, "_route_to_hr", return_value=True) as mock_hr,
    ):
        out = r._handle_general_query(email_data)

    assert out is True
    r.query_responder.generate_response.assert_called_once_with(
        "Etapy", "Ile etapów?", "candidate@test.com", rag_context=None
    )
    mock_send.assert_called_once()
    mock_notify.assert_called_once()
    mock_hr.assert_not_called()


def test_handle_general_query_rag_answer_searches_rag_and_sends_response():
    r = _make_router()
    if r is None:
        pytest.skip("EmailRouter init requires DB/agents")

    rag_results = [{"document": "CV przechowujemy przez 6 miesięcy", "metadata": {"source": "policy"}}]
    r.query_classifier = MagicMock()
    r.query_classifier.classify_query.return_value = {
        "action": "rag_answer",
        "confidence": 0.7,
        "reasoning": "policy question",
    }
    r.query_responder = MagicMock()
    r.query_responder.generate_response.return_value = "Odpowiedź z RAG\n\nZ wyrazami szacunku\n\nDział HR"
    r.rag_validator = MagicMock()
    r.rag_validator.validate_rag_response.return_value = SimpleNamespace(
        is_approved=True, reasoning="ok", issues_found=[], factual_errors=[]
    )
    rag_db = MagicMock()
    rag_db.search.return_value = rag_results

    email_data = {
        "from_email": "candidate@test.com",
        "subject": "RODO",
        "body": "Jak długo przechowujecie CV?",
    }
    with (
        patch.object(r, "_get_rag_db", return_value=rag_db),
        patch.object(r, "_send_email", return_value=True) as mock_send,
        patch.object(r, "_notify_hr_about_auto_response") as mock_notify,
        patch.object(r, "_route_to_hr", return_value=True) as mock_hr,
    ):
        out = r._handle_general_query(email_data)

    assert out is True
    rag_db.search.assert_called_once_with("RODO Jak długo przechowujecie CV?", n_results=3)
    r.query_responder.generate_response.assert_called_once_with(
        "RODO", "Jak długo przechowujecie CV?", "candidate@test.com", rag_context=rag_results
    )
    r.rag_validator.validate_rag_response.assert_called_once()
    mock_send.assert_called_once()
    mock_notify.assert_called_once()
    mock_hr.assert_not_called()


def test_handle_general_query_rag_no_results_forwards_to_hr():
    r = _make_router()
    if r is None:
        pytest.skip("EmailRouter init requires DB/agents")

    r.query_classifier = MagicMock()
    r.query_classifier.classify_query.return_value = {
        "action": "rag_answer",
        "confidence": 0.7,
        "reasoning": "policy question",
    }
    r.query_responder = MagicMock()
    rag_db = MagicMock()
    rag_db.search.return_value = []

    with (
        patch.object(r, "_get_rag_db", return_value=rag_db),
        patch.object(r, "_route_to_hr", return_value=True) as mock_hr,
    ):
        out = r._handle_general_query(
            {"from_email": "candidate@test.com", "subject": "RODO", "body": "Retencja?"}
        )

    assert out is True
    mock_hr.assert_called_once()

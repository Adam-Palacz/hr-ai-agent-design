"""
Live integration tests (real OpenAI, real SMTP).

Run only when explicitly enabled — uses credentials from .env:

  LIVE_TEST=1 pytest tests/test_live_integration.py -v -s

Optional: LIVE_TEST_EMAIL_TO=you@example.com  (override SMTP recipient for smoke test)
"""

from __future__ import annotations

import os
import time

import pytest
from dotenv import load_dotenv

load_dotenv()

from config import settings
from models.cv_models import CVData
from models.feedback_models import Decision, HRFeedback
from models.job_models import JobOffer
from tests.evaluation_criteria import (
    REFERENCE_CANDIDATE_EMAIL,
    REFERENCE_COMPANY,
    REFERENCE_POSITION,
    evaluate_feedback_html,
    llm_eval_api_configured,
)

pytestmark = pytest.mark.live


def _live_enabled() -> bool:
    return os.environ.get("LIVE_TEST", "").strip() in ("1", "true", "yes")


def _email_configured() -> bool:
    return bool(settings.email_username and settings.email_password)


def _no_mailbox_loop() -> bool:
    user = (settings.email_username or "").lower()
    hr = (settings.hr_email or "").lower()
    iod = (settings.iod_email or "").lower()
    return user not in (hr, iod) and user != ""


@pytest.fixture
def live_cv():
    return CVData(
        full_name="Jan Testowy (live)",
        email=REFERENCE_CANDIDATE_EMAIL,
        summary="Python, REST API, 5 lat doświadczenia, SQL.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )


@pytest.fixture
def live_hr_feedback():
    return HRFeedback(
        decision=Decision.REJECTED,
        notes="Solidne umiejętności techniczne; brak doświadczenia w fintech.",
        position_applied=REFERENCE_POSITION,
        interviewer_name="HR Team (live test)",
    )


@pytest.fixture
def live_job():
    return JobOffer(
        title=REFERENCE_POSITION,
        company=REFERENCE_COMPANY,
        location="Warszawa",
        description="Python, REST, SQL.",
    )


@pytest.mark.skipif(not _live_enabled(), reason="Set LIVE_TEST=1")
@pytest.mark.skipif(not llm_eval_api_configured(), reason="No LLM API key")
def test_live_llm_feedback_service_with_validation(live_cv, live_hr_feedback, live_job):
    from agents.correction_agent import FeedbackCorrectionAgent
    from agents.feedback_agent import FeedbackAgent
    from agents.validation_agent import FeedbackValidatorAgent
    from services.feedback_service import FeedbackService

    service = FeedbackService(
        FeedbackAgent(),
        FeedbackValidatorAgent(),
        FeedbackCorrectionAgent(),
        max_validation_iterations=3,
    )
    feedback, is_validated, error_info = service.generate_feedback(
        live_cv,
        live_hr_feedback,
        job_offer=live_job,
        enable_validation=True,
    )

    assert feedback.html_content
    assert is_validated is True, f"Validation failed: {error_info}"
    failures = evaluate_feedback_html(
        feedback.html_content,
        position=REFERENCE_POSITION,
        candidate_emails=[REFERENCE_CANDIDATE_EMAIL],
    )
    assert failures == [], "Criteria:\n- " + "\n- ".join(failures)


@pytest.mark.skipif(not _live_enabled(), reason="Set LIVE_TEST=1")
@pytest.mark.skipif(not _email_configured(), reason="EMAIL_USERNAME/PASSWORD not set")
@pytest.mark.skipif(not _no_mailbox_loop(), reason="EMAIL_USERNAME must differ from HR_EMAIL/IOD_EMAIL")
def test_live_smtp_send_smoke():
    from services.email_sender import send_email_gmail

    recipient = os.environ.get("LIVE_TEST_EMAIL_TO") or settings.hr_email
    assert recipient, "Set HR_EMAIL or LIVE_TEST_EMAIL_TO"

    subject = "[Recruitment AI LIVE_TEST] SMTP smoke test"
    body = "<p>Ten mail potwierdza działanie SMTP z aplikacji Recruitment AI (test automatyczny).</p>"

    ok, message_id = send_email_gmail(recipient, subject, body)
    assert ok is True, "SMTP send failed — check credentials and provider settings"
    assert message_id


@pytest.mark.skipif(not _live_enabled(), reason="Set LIVE_TEST=1")
@pytest.mark.skipif(not llm_eval_api_configured(), reason="No LLM API key")
@pytest.mark.skipif(not _email_configured(), reason="Email not configured")
@pytest.mark.skipif(not _no_mailbox_loop(), reason="EMAIL_USERNAME must differ from HR/IOD")
def test_live_e2e_generate_feedback_and_send_email(live_cv, live_hr_feedback, live_job):
    """E2E: real LLM feedback + real SMTP to LIVE_TEST_EMAIL_TO (or HR_EMAIL)."""
    from agents.feedback_agent import FeedbackAgent
    from services.email_sender import send_email_gmail
    from services.feedback_service import FeedbackService

    service = FeedbackService(FeedbackAgent(), validator_agent=None, correction_agent=None)
    feedback, is_validated, _ = service.generate_feedback(
        live_cv,
        live_hr_feedback,
        job_offer=live_job,
        enable_validation=False,
    )
    assert is_validated is True
    assert feedback.html_content

    recipient = os.environ.get("LIVE_TEST_EMAIL_TO") or settings.hr_email
    subject = f"[Recruitment AI E2E] Feedback test – {REFERENCE_POSITION}"
    ok, message_id = send_email_gmail(recipient, subject, feedback.html_content)
    assert ok is True, "Failed to send generated feedback via SMTP"
    assert message_id


@pytest.mark.skipif(not _live_enabled(), reason="Set LIVE_TEST=1")
@pytest.mark.skipif(not llm_eval_api_configured(), reason="No LLM API key")
def test_live_email_classifier_iod_sample():
    from agents.email_classifier_agent import EmailClassifierAgent

    agent = EmailClassifierAgent()
    result = agent.classify_email(
        "kandydat@example.com",
        "RODO – żądanie",
        "Proszę o informację, jak przetwarzane są moje dane osobowe w procesie rekrutacji.",
    )
    assert result.category == "iod"
    assert result.confidence >= 0.5

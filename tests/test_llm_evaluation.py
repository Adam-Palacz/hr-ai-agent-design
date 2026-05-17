"""
LLM evaluation tests: automated quality criteria + optional real API run.

  pytest tests/test_llm_evaluation.py -v
  RUN_LLM_EVAL=1 pytest tests/test_llm_evaluation.py -m evaluation -v
"""

import json
import os

import pytest
from unittest.mock import MagicMock, patch

from models.cv_models import CVData
from models.feedback_models import Decision, HRFeedback
from models.job_models import JobOffer
from tests.evaluation_criteria import (
    REFERENCE_CANDIDATE_EMAIL,
    REFERENCE_CANDIDATE_NAME,
    REFERENCE_COMPANY,
    REFERENCE_POSITION,
    check_html_valid,
    check_length_reasonable,
    check_no_disallowed_words,
    check_no_discriminatory_language,
    check_no_email_leak,
    check_rejection_tone,
    evaluate_feedback_html,
    llm_eval_api_configured,
)


@pytest.fixture
def good_html():
    return (
        "<!DOCTYPE html><html><body>"
        "<p>Szanowny Kandydacie,</p>"
        "<p>Dziękujemy za złożenie aplikacji na stanowisko Backend Developer.</p>"
        "<p>Z przykrością informujemy, że zdecydowaliśmy się procedować z innymi kandydatami.</p>"
        "<p>Na podstawie CV stwierdzono solidne umiejętności techniczne.</p>"
        "<p>Pozdrawiamy,</p><p>Zespół HR</p>"
        "</body></html>"
    )


@pytest.fixture
def reference_cv():
    return CVData(
        full_name=REFERENCE_CANDIDATE_NAME,
        email=REFERENCE_CANDIDATE_EMAIL,
        summary="Python, REST, SQL, 5 lat doświadczenia.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )


@pytest.fixture
def reference_hr_feedback():
    return HRFeedback(
        decision=Decision.REJECTED,
        notes="Dobre umiejętności techniczne, brak doświadczenia w domenie fintech.",
        position_applied=REFERENCE_POSITION,
        interviewer_name="HR Team",
    )


@pytest.fixture
def reference_job_offer():
    return JobOffer(
        title=REFERENCE_POSITION,
        company=REFERENCE_COMPANY,
        location="Warszawa",
        description="Python, REST APIs, SQL.",
    )


# --- Criteria unit tests ---


def test_evaluation_criteria_valid_html_passes(good_html):
    assert check_html_valid(good_html) is True


def test_evaluation_criteria_length_passes(good_html):
    assert check_length_reasonable(good_html) is True


def test_evaluation_criteria_disallowed_words_fails():
    assert check_no_disallowed_words("<p>Hello</p><p>TODO: add more</p>") is False


def test_evaluation_criteria_disallowed_words_passes(good_html):
    assert check_no_disallowed_words(good_html) is True


def test_evaluation_criteria_email_leak_fails():
    assert check_no_email_leak("<p>Contact: user@example.com</p>", []) is False


def test_evaluation_criteria_email_leak_passes(good_html):
    assert check_no_email_leak(good_html, [REFERENCE_CANDIDATE_EMAIL]) is True


def test_evaluation_criteria_rejection_tone(good_html):
    assert check_rejection_tone(good_html) is True
    assert check_rejection_tone("<p>Dziękujemy za aplikację.</p>") is False


def test_evaluation_criteria_discriminatory_fails():
    assert check_no_discriminatory_language("<p>Kandydat jest za stary na to stanowisko.</p>") is False


def test_evaluate_feedback_html_all_pass(good_html):
    assert evaluate_feedback_html(
        good_html,
        position=REFERENCE_POSITION,
        candidate_emails=[REFERENCE_CANDIDATE_EMAIL],
    ) == []


# --- Mock LLM pipeline ---


@patch("agents.base_agent.get_llm_client")
def test_evaluation_mock_llm_output_passes_all_criteria(
    mock_get_llm, good_html, reference_cv, reference_hr_feedback
):
    from agents.feedback_agent import FeedbackAgent

    mock_adapter = MagicMock()
    payload = json.dumps({"html_content": good_html})
    mock_adapter.complete.return_value = (payload, MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = FeedbackAgent(model_name="gpt-4o-mini")
    result = agent.generate_feedback(reference_cv, reference_hr_feedback)

    failures = evaluate_feedback_html(
        result.html_content,
        position=REFERENCE_POSITION,
        candidate_emails=[REFERENCE_CANDIDATE_EMAIL],
    )
    assert failures == [], f"Criteria failures: {failures}"


@patch("agents.base_agent.get_llm_client")
def test_evaluation_full_service_with_validation_mock(
    mock_get_llm, good_html, reference_cv, reference_hr_feedback, reference_job_offer
):
    """FeedbackService end-to-end on mocks: generate + validate + criteria."""
    from agents.correction_agent import FeedbackCorrectionAgent
    from agents.feedback_agent import FeedbackAgent
    from agents.validation_agent import FeedbackValidatorAgent
    from services.feedback_service import FeedbackService

    validation_approved = json.dumps(
        {
            "status": "approved",
            "is_approved": True,
            "reasoning": "OK",
            "issues_found": [],
            "ethical_concerns": [],
            "factual_errors": [],
            "suggestions": [],
        }
    )
    mock_adapter = MagicMock()
    mock_adapter.complete.side_effect = [
        (json.dumps({"html_content": good_html}), MagicMock()),
        (validation_approved, MagicMock()),
    ]
    mock_get_llm.return_value = mock_adapter

    service = FeedbackService(
        FeedbackAgent(model_name="gpt-4o-mini"),
        FeedbackValidatorAgent(model_name="gpt-4o-mini"),
        FeedbackCorrectionAgent(model_name="gpt-4o-mini"),
        max_validation_iterations=3,
    )
    feedback, is_validated, error_info = service.generate_feedback(
        reference_cv,
        reference_hr_feedback,
        job_offer=reference_job_offer,
        enable_validation=True,
    )

    assert is_validated is True
    assert error_info is None
    failures = evaluate_feedback_html(
        feedback.html_content,
        position=REFERENCE_POSITION,
        candidate_emails=[REFERENCE_CANDIDATE_EMAIL],
    )
    assert failures == []


# --- Real LLM (optional) ---


@pytest.mark.evaluation
@pytest.mark.skipif(not os.environ.get("RUN_LLM_EVAL"), reason="Set RUN_LLM_EVAL=1 to run")
@pytest.mark.skipif(not llm_eval_api_configured(), reason="No API key for LLM_PROVIDER")
def test_evaluation_real_llm_feedback_quality(
    reference_cv, reference_hr_feedback, reference_job_offer
):
    """Calls the real LLM once; asserts automated quality criteria on output."""
    from agents.feedback_agent import FeedbackAgent

    agent = FeedbackAgent()
    feedback = agent.generate_feedback(
        reference_cv,
        reference_hr_feedback,
        job_offer=reference_job_offer,
    )

    assert feedback.html_content, "Model returned empty html_content"

    failures = evaluate_feedback_html(
        feedback.html_content,
        position=REFERENCE_POSITION,
        candidate_emails=[REFERENCE_CANDIDATE_EMAIL],
    )
    assert failures == [], "Real LLM output failed criteria:\n- " + "\n- ".join(failures)

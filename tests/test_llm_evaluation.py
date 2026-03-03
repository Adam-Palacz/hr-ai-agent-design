"""
LLM evaluation tests: reference inputs and automated criteria (structure, length, disallowed words).

- With mock LLM: run always (sanity check that evaluation pipeline works).
- With real LLM: run only when RUN_LLM_EVAL=1 (optional; for prompt/model changes).

Usage:
  pytest tests/test_llm_evaluation.py -v
  RUN_LLM_EVAL=1 pytest tests/test_llm_evaluation.py -v -m evaluation  # optional real API
"""

import os
import re
import pytest
from unittest.mock import patch, MagicMock

# Reference input (anonymized/synthetic)
REFERENCE_CV_TEXT = (
    "John Doe\n"
    "Email: john.doe@example.com\n"
    "5+ years Python, REST APIs, SQL.\n"
    "Education: MSc Computer Science, University of Warsaw.\n"
    "Experience: Backend Developer at Tech Corp 2020–2024."
)
REFERENCE_POSITION = "Backend Developer"


def check_html_valid(html: str) -> bool:
    """Ensure output is valid HTML (reuse project validation)."""
    if not html or not isinstance(html, str):
        return False
    from models.validation_models import _is_parseable_html, _is_likely_html

    return _is_likely_html(html) and _is_parseable_html(html)


def check_length_reasonable(html: str, min_len: int = 200, max_len: int = 5000) -> bool:
    """Output length should be in a reasonable range."""
    return min_len <= len(html) <= max_len


DISALLOWED_WORDS = ["TODO", "Lorem", "INSERT", "FIXME", "XXX"]


def check_no_disallowed_words(html: str, words: list[str] | None = None) -> bool:
    """No placeholder or disallowed words in output."""
    words = words or DISALLOWED_WORDS
    return not any(w in html for w in words)


def check_no_email_leak(html: str) -> bool:
    """No raw email pattern (simple check for obvious leak)."""
    # Allow e.g. mailto: or masked; disallow obvious user@domain
    pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    return re.search(pattern, html) is None


# --- Tests with mock LLM ---


@pytest.fixture
def good_html():
    """Valid, reasonable feedback HTML for evaluation criteria."""
    return (
        "<!DOCTYPE html><html><body>"
        "<p>Dear Candidate,</p>"
        "<p>Thank you for your application to the Backend Developer position.</p>"
        "<p>We have carefully reviewed your experience and skills.</p>"
        "<p>Unfortunately we have decided to pursue other candidates at this time.</p>"
        "<p>We wish you success in your job search.</p>"
        "<p>Best regards,</p><p>HR Team</p>"
        "</body></html>"
    )


def test_evaluation_criteria_valid_html_passes(good_html):
    """Evaluation: valid HTML passes check_html_valid."""
    assert check_html_valid(good_html) is True


def test_evaluation_criteria_length_passes(good_html):
    """Evaluation: reasonable length passes check_length_reasonable."""
    assert check_length_reasonable(good_html) is True


def test_evaluation_criteria_disallowed_words_fails():
    """Evaluation: HTML containing TODO fails check_no_disallowed_words."""
    html_with_todo = "<p>Hello</p><p>TODO: add more</p>"
    assert check_no_disallowed_words(html_with_todo) is False


def test_evaluation_criteria_disallowed_words_passes(good_html):
    """Evaluation: clean HTML passes check_no_disallowed_words."""
    assert check_no_disallowed_words(good_html) is True


def test_evaluation_criteria_email_leak_fails():
    """Evaluation: HTML containing raw email fails check_no_email_leak."""
    html_with_email = "<p>Contact: user@example.com</p>"
    assert check_no_email_leak(html_with_email) is False


def test_evaluation_criteria_email_leak_passes(good_html):
    """Evaluation: HTML without raw email passes check_no_email_leak."""
    assert check_no_email_leak(good_html) is True


@patch("agents.base_agent.get_llm_client")
def test_evaluation_mock_llm_output_passes_all_criteria(mock_get_llm, good_html):
    """With mock LLM returning good HTML, all evaluation criteria pass."""
    import json
    from agents.feedback_agent import FeedbackAgent
    from models.cv_models import CVData
    from models.feedback_models import HRFeedback, Decision

    mock_adapter = MagicMock()
    completion = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({"html_content": good_html})))],
        usage=MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )
    mock_adapter.complete.return_value = (json.dumps({"html_content": good_html}), completion)
    mock_get_llm.return_value = mock_adapter

    agent = FeedbackAgent(model_name="gpt-4o-mini")
    cv = CVData(
        full_name="John Doe",
        email="john@example.com",
        summary="5 years Python.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )
    hr = HRFeedback(
        decision=Decision.REJECTED,
        notes="Strong technical skills.",
        position_applied=REFERENCE_POSITION,
        interviewer_name="HR",
    )
    result = agent.generate_feedback(cv, hr)

    assert check_html_valid(result.html_content)
    assert check_length_reasonable(result.html_content)
    assert check_no_disallowed_words(result.html_content)
    assert check_no_email_leak(result.html_content)


@pytest.mark.evaluation
@pytest.mark.skipif(not os.environ.get("RUN_LLM_EVAL"), reason="RUN_LLM_EVAL=1 not set")
def test_evaluation_real_llm_optional():
    """Optional: run with real LLM (RUN_LLM_EVAL=1) to evaluate model output. Skipped by default."""
    pytest.skip("Real LLM evaluation: run manually with RUN_LLM_EVAL=1 and API key")

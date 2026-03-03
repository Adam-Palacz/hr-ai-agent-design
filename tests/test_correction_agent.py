"""Unit tests for correction agent (mocked LLM)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from models.cv_models import CVData
from models.feedback_models import HRFeedback, Decision
from models.validation_models import ValidationResult, ValidationStatus


def _make_completion(content: str):
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    mock.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return mock


@pytest.fixture
def sample_cv_data():
    return CVData(
        full_name="Jan Testowy",
        email="jan@example.com",
        summary="Python developer.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )


@pytest.fixture
def sample_hr_feedback():
    return HRFeedback(
        decision=Decision.REJECTED,
        notes="Good skills.",
        position_applied="Backend Developer",
        interviewer_name="HR Team",
    )


@pytest.fixture
def sample_validation_result():
    return ValidationResult(
        status=ValidationStatus.REJECTED,
        is_approved=False,
        reasoning="Tone too informal.",
        issues_found=["Use formal greeting"],
        ethical_concerns=[],
        factual_errors=[],
        suggestions=[],
    )


@patch("agents.base_agent.get_llm_client")
def test_correction_agent_returns_corrected_feedback(
    mock_get_llm, sample_cv_data, sample_hr_feedback, sample_validation_result
):
    """Given original HTML and validation result, agent returns CorrectedFeedback with html_content and corrections_made."""
    corrected_html = "<p>Dear Jan,</p><p>Thank you for your application.</p>"
    correction_json = json.dumps(
        {
            "html_content": corrected_html,
            "corrections_made": ["Adjusted greeting to formal tone"],
            "explanation": "Updated to formal language.",
        }
    )
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (correction_json, _make_completion(correction_json))
    mock_get_llm.return_value = mock_adapter

    from agents.correction_agent import FeedbackCorrectionAgent

    agent = FeedbackCorrectionAgent(model_name="gpt-4o-mini")
    result = agent.correct_feedback(
        "<p>Hey</p>",
        sample_validation_result,
        sample_cv_data,
        sample_hr_feedback,
    )

    assert result.html_content == corrected_html
    assert len(result.corrections_made) > 0
    mock_adapter.complete.assert_called_once()
    call_messages = mock_adapter.complete.call_args[1]["messages"]
    user_content = next(
        (m.get("content", "") for m in call_messages if m.get("role") == "user"), ""
    )
    assert (
        "formal" in user_content.lower()
        or "greeting" in user_content.lower()
        or "informal" in user_content.lower()
    )

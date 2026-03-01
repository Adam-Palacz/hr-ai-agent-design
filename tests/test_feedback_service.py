"""Unit tests for feedback_service (mocked LLM, no real API)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from models.cv_models import CVData
from models.feedback_models import HRFeedback, CandidateFeedback, Decision


def _make_completion(content: str):
    """Build a mock chat completion with given message content."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    mock.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return mock


@pytest.fixture
def sample_cv_data():
    """Minimal CVData."""
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
    """Minimal HRFeedback."""
    return HRFeedback(
        decision=Decision.REJECTED,
        notes="Good skills.",
        position_applied="Backend Developer",
        interviewer_name="HR Team",
    )


@patch("agents.base_agent.AzureOpenAI")
def test_generate_feedback_success_returns_candidate_feedback(
    mock_azure, sample_cv_data, sample_hr_feedback
):
    """Successful generation returns CandidateFeedback with html_content and is_validated True when validation is skipped."""
    html = "<p>Dear Jan,</p><p>Thank you for applying.</p>"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion(
        json.dumps({"html_content": html})
    )
    mock_azure.return_value = mock_client

    from agents.feedback_agent import FeedbackAgent
    from services.feedback_service import FeedbackService

    feedback_agent = FeedbackAgent(model_name="gpt-4o-mini")
    service = FeedbackService(feedback_agent, validator_agent=None, correction_agent=None)

    feedback, is_validated, error_info = service.generate_feedback(
        sample_cv_data, sample_hr_feedback, enable_validation=False
    )

    assert isinstance(feedback, CandidateFeedback)
    assert feedback.html_content is not None
    assert "Jan" in feedback.html_content or "html" in feedback.html_content.lower()
    assert is_validated is True
    assert error_info is None
    assert mock_client.chat.completions.create.called


@patch("agents.base_agent.AzureOpenAI")
def test_generate_feedback_validation_approved_returns_validated(
    mock_azure, sample_cv_data, sample_hr_feedback
):
    """When validation is enabled and validator returns approved, is_validated is True."""
    html = "<!DOCTYPE html><html><body><p>Dear Jan,</p></body></html>"
    validation_json = json.dumps(
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

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _make_completion(json.dumps({"html_content": html})),
        _make_completion(validation_json),
    ]
    mock_azure.return_value = mock_client

    from agents.feedback_agent import FeedbackAgent
    from agents.validation_agent import FeedbackValidatorAgent
    from agents.correction_agent import FeedbackCorrectionAgent
    from services.feedback_service import FeedbackService

    feedback_agent = FeedbackAgent(model_name="gpt-4o-mini")
    validator = FeedbackValidatorAgent(model_name="gpt-4o-mini")
    corrector = FeedbackCorrectionAgent(model_name="gpt-4o-mini")
    service = FeedbackService(feedback_agent, validator_agent=validator, correction_agent=corrector)

    feedback, is_validated, error_info = service.generate_feedback(
        sample_cv_data, sample_hr_feedback, enable_validation=True
    )

    assert feedback.html_content is not None
    assert is_validated is True
    assert error_info is None


@patch("agents.base_agent.AzureOpenAI")
def test_generate_feedback_llm_error_raises(mock_azure, sample_cv_data, sample_hr_feedback):
    """When LLM raises, FeedbackService raises LLMError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")
    mock_azure.return_value = mock_client

    from agents.feedback_agent import FeedbackAgent
    from services.feedback_service import FeedbackService
    from core.exceptions import LLMError

    feedback_agent = FeedbackAgent(model_name="gpt-4o-mini")
    service = FeedbackService(feedback_agent, validator_agent=None, correction_agent=None)

    with pytest.raises(LLMError) as exc_info:
        service.generate_feedback(sample_cv_data, sample_hr_feedback, enable_validation=False)

    assert "Failed to generate feedback" in str(exc_info.value) or "API error" in str(
        exc_info.value
    )

"""Unit tests for validation agent (mocked LLM)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from models.cv_models import CVData
from models.feedback_models import HRFeedback, Decision


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


@patch("agents.base_agent.get_llm_client")
def test_validation_agent_approved_returns_validation_result(
    mock_get_llm, sample_cv_data, sample_hr_feedback
):
    """When LLM returns approved JSON, agent returns ValidationResult with is_approved True."""
    validation_json = json.dumps(
        {
            "status": "approved",
            "is_approved": True,
            "reasoning": "Feedback is appropriate.",
            "issues_found": [],
            "ethical_concerns": [],
            "factual_errors": [],
            "suggestions": [],
        }
    )
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (validation_json, _make_completion(validation_json))
    mock_get_llm.return_value = mock_adapter

    from agents.validation_agent import FeedbackValidatorAgent

    agent = FeedbackValidatorAgent(model_name="gpt-4o-mini")
    result = agent.validate_feedback("<p>Hello</p>", sample_cv_data, sample_hr_feedback)

    assert result.is_approved is True
    assert result.status.value == "approved"
    assert "reasoning" in result.reasoning.lower() or "appropriate" in result.reasoning.lower()


@patch("agents.base_agent.get_llm_client")
def test_validation_agent_rejected_returns_issues(mock_get_llm, sample_cv_data, sample_hr_feedback):
    """When LLM returns rejected JSON, agent returns ValidationResult with issues_found."""
    validation_json = json.dumps(
        {
            "status": "rejected",
            "is_approved": False,
            "reasoning": "Tone too informal.",
            "issues_found": ["Informal language"],
            "ethical_concerns": [],
            "factual_errors": [],
            "suggestions": ["Use formal tone"],
        }
    )
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (validation_json, _make_completion(validation_json))
    mock_get_llm.return_value = mock_adapter

    from agents.validation_agent import FeedbackValidatorAgent

    agent = FeedbackValidatorAgent(model_name="gpt-4o-mini")
    result = agent.validate_feedback("<p>Hey there</p>", sample_cv_data, sample_hr_feedback)

    assert result.is_approved is False
    assert result.status.value == "rejected"
    assert len(result.issues_found) > 0
    assert "Informal" in result.issues_found[0] or "informal" in str(result.issues_found)

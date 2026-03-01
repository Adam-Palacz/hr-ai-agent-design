"""Unit tests for feedback agent (mocked LLM)."""

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


@patch("agents.base_agent.AzureOpenAI")
def test_feedback_agent_returns_html_content(mock_azure, sample_cv_data, sample_hr_feedback):
    """Given valid CV and HR feedback, agent returns CandidateFeedback with HTML."""
    html = "<p>Dear Jan,</p><p>Thank you for applying.</p>"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_completion(
        json.dumps({"html_content": html})
    )
    mock_azure.return_value = mock_client

    from agents.feedback_agent import FeedbackAgent

    agent = FeedbackAgent(model_name="gpt-4o-mini")
    result = agent.generate_feedback(sample_cv_data, sample_hr_feedback)

    assert result.html_content is not None
    assert "<" in result.html_content and ">" in result.html_content
    mock_client.chat.completions.create.assert_called_once()
    call_messages = mock_client.chat.completions.create.call_args[1]["messages"]
    assert any("Jan" in (m.get("content") or "") for m in call_messages)


@patch("agents.base_agent.AzureOpenAI")
def test_feedback_agent_llm_error_propagates(mock_azure, sample_cv_data, sample_hr_feedback):
    """When LLM raises, agent propagates exception."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API error")
    mock_azure.return_value = mock_client

    from agents.feedback_agent import FeedbackAgent

    agent = FeedbackAgent(model_name="gpt-4o-mini")
    with pytest.raises(Exception) as exc_info:
        agent.generate_feedback(sample_cv_data, sample_hr_feedback)

    assert "API error" in str(exc_info.value)

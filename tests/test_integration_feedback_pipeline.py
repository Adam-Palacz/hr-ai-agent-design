"""
Integration tests for feedback pipeline: CV -> parse -> generate -> validate (all with mocks).

Run with: pytest tests/test_integration_feedback_pipeline.py -v
No real OpenAI, DB, or email required.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from models.cv_models import CVData
from models.feedback_models import HRFeedback, CandidateFeedback, Decision


def _make_completion(content: str):
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    mock.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return mock


@pytest.mark.integration
@patch("agents.base_agent.get_llm_client")
def test_feedback_pipeline_generate_validate_approved(mock_get_llm):
    """Full pipeline: generate feedback -> validate (approved) -> final result has html_content and is_validated True."""
    html = "<!DOCTYPE html><html><body><p>Dear Jan,</p><p>Thank you for applying.</p></body></html>"
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
        (json.dumps({"html_content": html}), _make_completion(json.dumps({"html_content": html}))),
        (validation_approved, _make_completion(validation_approved)),
    ]
    mock_get_llm.return_value = mock_adapter

    from agents.feedback_agent import FeedbackAgent
    from agents.validation_agent import FeedbackValidatorAgent
    from agents.correction_agent import FeedbackCorrectionAgent
    from services.feedback_service import FeedbackService

    cv_data = CVData(
        full_name="Jan Testowy",
        email="jan@example.com",
        summary="Python developer.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )
    hr_feedback = HRFeedback(
        decision=Decision.REJECTED,
        notes="Strong technical skills.",
        position_applied="Backend Developer",
        interviewer_name="HR Team",
    )

    feedback_agent = FeedbackAgent(model_name="gpt-4o-mini")
    validator = FeedbackValidatorAgent(model_name="gpt-4o-mini")
    corrector = FeedbackCorrectionAgent(model_name="gpt-4o-mini")
    service = FeedbackService(
        feedback_agent,
        validator_agent=validator,
        correction_agent=corrector,
        max_validation_iterations=3,
    )

    feedback, is_validated, error_info = service.generate_feedback(
        cv_data, hr_feedback, enable_validation=True
    )

    assert isinstance(feedback, CandidateFeedback)
    assert feedback.html_content is not None
    assert "html" in feedback.html_content.lower() or "<" in feedback.html_content
    assert is_validated is True
    assert error_info is None


@pytest.mark.integration
@patch("agents.base_agent.get_llm_client")
def test_feedback_pipeline_rejected_then_corrected(mock_get_llm):
    """Pipeline: generate -> validate (rejected) -> correct -> final feedback is corrected HTML."""
    html1 = "<p>Hey Jan,</p><p>Thanks.</p>"
    validation_rejected = json.dumps(
        {
            "status": "rejected",
            "is_approved": False,
            "reasoning": "Use formal tone.",
            "issues_found": ["Informal greeting"],
            "ethical_concerns": [],
            "factual_errors": [],
            "suggestions": ["Use Dear Jan"],
        }
    )
    html2 = "<p>Dear Jan,</p><p>Thank you for your application.</p>"
    correction_json = json.dumps(
        {
            "html_content": html2,
            "corrections_made": ["Formal greeting"],
            "explanation": "Updated greeting.",
        }
    )
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
        (
            json.dumps({"html_content": html1}),
            _make_completion(json.dumps({"html_content": html1})),
        ),
        (validation_rejected, _make_completion(validation_rejected)),
        (correction_json, _make_completion(correction_json)),
        (validation_approved, _make_completion(validation_approved)),
    ]
    mock_get_llm.return_value = mock_adapter

    from agents.feedback_agent import FeedbackAgent
    from agents.validation_agent import FeedbackValidatorAgent
    from agents.correction_agent import FeedbackCorrectionAgent
    from services.feedback_service import FeedbackService

    cv_data = CVData(
        full_name="Jan Testowy",
        email="jan@example.com",
        summary="Python developer.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )
    hr_feedback = HRFeedback(
        decision=Decision.REJECTED,
        notes="Good skills.",
        position_applied="Backend Developer",
        interviewer_name="HR Team",
    )

    feedback_agent = FeedbackAgent(model_name="gpt-4o-mini")
    validator = FeedbackValidatorAgent(model_name="gpt-4o-mini")
    corrector = FeedbackCorrectionAgent(model_name="gpt-4o-mini")
    service = FeedbackService(
        feedback_agent,
        validator_agent=validator,
        correction_agent=corrector,
        max_validation_iterations=3,
    )

    feedback, is_validated, error_info = service.generate_feedback(
        cv_data, hr_feedback, enable_validation=True
    )

    assert feedback.html_content is not None
    assert "Dear" in feedback.html_content
    assert is_validated is True
    assert error_info is None

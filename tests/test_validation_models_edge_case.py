"""Edge case: invalid HTML in CorrectedFeedback should raise ValueError (validation_models)."""

import pytest
from pydantic import ValidationError

from models.validation_models import CorrectedFeedback


def test_corrected_feedback_rejects_plain_text():
    """CorrectedFeedback validator should reject content without HTML markup."""
    with pytest.raises(ValidationError) as exc_info:
        CorrectedFeedback(
            html_content="Plain text without any tags",
            corrections_made=[],
            explanation="Test",
        )
    assert (
        "html_content" in str(exc_info.value)
        or "markup" in str(exc_info.value).lower()
        or "valid" in str(exc_info.value).lower()
    )


def test_corrected_feedback_accepts_valid_html():
    """CorrectedFeedback accepts well-formed HTML."""
    cf = CorrectedFeedback(
        html_content="<p>Hello</p><p>World</p>",
        corrections_made=["Fixed greeting"],
        explanation="Test",
    )
    assert cf.html_content == "<p>Hello</p><p>World</p>"
    assert cf.corrections_made == ["Fixed greeting"]

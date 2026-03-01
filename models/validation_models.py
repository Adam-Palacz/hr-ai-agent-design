"""Pydantic models for feedback validation and correction."""

from typing import Optional, List
from enum import Enum
from html.parser import HTMLParser

from pydantic import BaseModel, Field, field_validator


class ValidationStatus(str, Enum):
    """Validation status enum."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ValidationResult(BaseModel):
    """Result of feedback validation."""

    status: ValidationStatus = Field(..., description="Validation status: approved or rejected")
    is_approved: bool = Field(
        ..., description="Whether the feedback is approved (True) or rejected (False)"
    )
    reasoning: str = Field(
        ...,
        description="Detailed reasoning for the validation decision. If rejected, must explain what issues were found and why.",
    )
    issues_found: List[str] = Field(
        default_factory=list, description="List of specific issues found (only if rejected)"
    )
    ethical_concerns: List[str] = Field(
        default_factory=list,
        description="List of ethical concerns (discrimination, offensive content, etc.)",
    )
    factual_errors: List[str] = Field(
        default_factory=list, description="List of factual errors or inconsistencies"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for improvement (if rejected)"
    )


class CorrectionRequest(BaseModel):
    """Request for feedback correction based on validation feedback."""

    original_html_content: str = Field(
        ..., description="Original HTML feedback content that needs correction"
    )
    validation_reasoning: str = Field(
        ..., description="Reasoning from the validator explaining why the feedback was rejected"
    )
    issues_found: List[str] = Field(
        default_factory=list, description="List of specific issues that need to be addressed"
    )
    ethical_concerns: List[str] = Field(
        default_factory=list, description="List of ethical concerns to address"
    )
    factual_errors: List[str] = Field(
        default_factory=list, description="List of factual errors to correct"
    )


class _HTMLParserStrict(HTMLParser):
    """HTMLParser that records parse errors."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors: List[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)


def _is_likely_html(value: str) -> bool:
    """Check that the string looks like HTML (contains markup)."""
    s = value.strip()
    return len(s) > 0 and "<" in s and ">" in s


def _is_parseable_html(value: str) -> bool:
    """Check that the string can be parsed as HTML without errors."""
    parser = _HTMLParserStrict()
    try:
        parser.feed(value)
        return len(parser.errors) == 0
    except Exception:
        return False


class CorrectedFeedback(BaseModel):
    """Corrected feedback after addressing validation issues."""

    html_content: str = Field(
        ...,
        description="Corrected HTML formatted feedback email ready to send",
        min_length=1,
    )
    corrections_made: List[str] = Field(
        default_factory=list, description="List of corrections that were made"
    )
    explanation: Optional[str] = Field(None, description="Brief explanation of what was corrected")

    @field_validator("html_content", mode="after")
    @classmethod
    def html_content_must_be_markup(cls, v: str) -> str:
        """Ensure html_content looks like HTML (contains tags), not plain text."""
        if not v or not v.strip():
            raise ValueError("html_content cannot be empty")
        if not _is_likely_html(v):
            raise ValueError(
                "html_content must contain HTML markup (e.g. <p>, <div>, <strong>); "
                "plain text without tags is not valid"
            )
        if not _is_parseable_html(v):
            raise ValueError(
                "html_content could not be parsed as valid HTML (check for unclosed tags or invalid entities)"
            )
        return v.strip()

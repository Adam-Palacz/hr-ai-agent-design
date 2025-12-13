"""Pydantic models for feedback validation and correction."""
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Validation status enum."""
    APPROVED = "approved"
    REJECTED = "rejected"


class ValidationResult(BaseModel):
    """Result of feedback validation."""
    status: ValidationStatus = Field(..., description="Validation status: approved or rejected")
    is_approved: bool = Field(..., description="Whether the feedback is approved (True) or rejected (False)")
    reasoning: str = Field(..., description="Detailed reasoning for the validation decision. If rejected, must explain what issues were found and why.")
    issues_found: List[str] = Field(default_factory=list, description="List of specific issues found (only if rejected)")
    ethical_concerns: List[str] = Field(default_factory=list, description="List of ethical concerns (discrimination, offensive content, etc.)")
    factual_errors: List[str] = Field(default_factory=list, description="List of factual errors or inconsistencies")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement (if rejected)")


class CorrectionRequest(BaseModel):
    """Request for feedback correction based on validation feedback."""
    original_html_content: str = Field(..., description="Original HTML feedback content that needs correction")
    validation_reasoning: str = Field(..., description="Reasoning from the validator explaining why the feedback was rejected")
    issues_found: List[str] = Field(default_factory=list, description="List of specific issues that need to be addressed")
    ethical_concerns: List[str] = Field(default_factory=list, description="List of ethical concerns to address")
    factual_errors: List[str] = Field(default_factory=list, description="List of factual errors to correct")


class CorrectedFeedback(BaseModel):
    """Corrected feedback after addressing validation issues."""
    html_content: str = Field(..., description="Corrected HTML formatted feedback email ready to send")
    corrections_made: List[str] = Field(default_factory=list, description="List of corrections that were made")
    explanation: Optional[str] = Field(None, description="Brief explanation of what was corrected")


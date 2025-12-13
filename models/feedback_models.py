"""Pydantic models for HR feedback and candidate feedback."""
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class FeedbackFormat(str, Enum):
    """Feedback output format options."""
    TEXT = "text"  # Plain text only
    HTML = "html"  # HTML only (default)
    BOTH = "both"  # Both text and HTML


class Decision(str, Enum):
    """Decision enum for candidate processing."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


class HRFeedback(BaseModel):
    """HR feedback model for candidate evaluation."""
    decision: Decision = Field(..., description="Final decision: accepted, rejected, or pending")
    strengths: List[str] = Field(default_factory=list, description="Candidate's strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Areas for improvement or concerns")
    notes: Optional[str] = Field(None, description="Additional notes from HR")
    position_applied: Optional[str] = Field(None, description="Position the candidate applied for")
    interviewer_name: Optional[str] = Field(None, description="Name of the interviewer or HR representative")
    missing_requirements: List[str] = Field(default_factory=list, description="Missing required qualifications")


class CandidateFeedback(BaseModel):
    """Personalized feedback model for candidates."""
    html_content: str = Field(..., description="Complete HTML formatted feedback email ready to send. This is the ONLY required field. The HTML should include greeting, decision announcement, strengths, improvement areas, next steps, and closing - all formatted as a complete HTML email with inline styles.")
    
    # Optional fields - COMMENTED OUT: prompt handles all logic, only html_content is needed
    # greeting: Optional[str] = Field(None, description="Optional: Personalized greeting (already in html_content)")
    # decision_announcement: Optional[str] = Field(None, description="Optional: Decision announcement (already in html_content)")
    # strengths_section: Optional[str] = Field(None, description="Optional: Strengths section (already in html_content)")
    # improvement_areas: Optional[str] = Field(None, description="Optional: Improvement areas (already in html_content)")
    # next_steps: Optional[str] = Field(None, description="Optional: Next steps (already in html_content)")
    # closing: Optional[str] = Field(None, description="Optional: Closing statement (already in html_content)")
    # full_feedback: Optional[str] = Field(None, description="Optional: Plain text version (if needed)")


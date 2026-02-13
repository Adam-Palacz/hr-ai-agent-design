"""Pydantic models for job offers."""

from typing import Optional
from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Job offer with description and basic details."""

    title: str = Field(..., description="Job title/position name")
    company: Optional[str] = Field(None, description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    description: str = Field(
        ...,
        description="Full job description as text - includes requirements, responsibilities, qualifications, etc.",
    )

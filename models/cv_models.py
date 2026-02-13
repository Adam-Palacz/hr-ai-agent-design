"""Pydantic models for CV data structure."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Education(BaseModel):
    """Education entry model."""

    institution: str = Field(..., description="Name of the educational institution")
    degree: str = Field(..., description="Degree obtained (e.g., Bachelor's, Master's)")
    field_of_study: Optional[str] = Field(None, description="Field of study or major")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM or YYYY) or 'Present'")
    gpa: Optional[float] = Field(None, description="GPA if mentioned")
    honors: Optional[str] = Field(None, description="Honors or distinctions")


class Experience(BaseModel):
    """Work experience entry model."""

    company: str = Field(..., description="Company name")
    position: str = Field(..., description="Job title/position")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM or YYYY) or 'Present'")
    description: Optional[str] = Field(None, description="Job description and responsibilities")
    achievements: Optional[List[str]] = Field(default_factory=list, description="Key achievements")


class Skill(BaseModel):
    """Skill entry model."""

    name: str = Field(..., description="Skill name")
    category: Optional[str] = Field(
        None, description="Skill category (e.g., Technical, Language, Soft)"
    )
    proficiency: Optional[str] = Field(
        None, description="Proficiency level (e.g., Beginner, Intermediate, Advanced, Expert)"
    )


class Certification(BaseModel):
    """Certification entry model."""

    name: str = Field(..., description="Certification name")
    issuer: Optional[str] = Field(None, description="Issuing organization")
    date: Optional[str] = Field(None, description="Date obtained (YYYY-MM or YYYY)")
    expiry_date: Optional[str] = Field(None, description="Expiry date if applicable")


class Language(BaseModel):
    """Language proficiency model."""

    language: str = Field(..., description="Language name")
    proficiency: str = Field(
        ..., description="Proficiency level (e.g., Native, Fluent, Intermediate, Basic)"
    )


class CVData(BaseModel):
    """Complete CV data structure."""

    full_name: str = Field(..., description="Candidate's full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Location or address")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(None, description="Portfolio website URL")

    summary: Optional[str] = Field(None, description="Professional summary or objective")

    education: List[Education] = Field(default_factory=list, description="Education history")
    experience: List[Experience] = Field(default_factory=list, description="Work experience")
    skills: List[Skill] = Field(default_factory=list, description="Skills list")
    certifications: List[Certification] = Field(default_factory=list, description="Certifications")
    languages: List[Language] = Field(default_factory=list, description="Languages")

    additional_info: Optional[str] = Field(None, description="Any additional relevant information")

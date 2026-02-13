"""Shared formatting utilities for agents."""

from models.cv_models import CVData
from models.feedback_models import HRFeedback
from models.job_models import JobOffer


def format_cv_data(cv_data: CVData) -> str:
    """Format CV data for prompt."""
    lines = [
        f"Name: {cv_data.full_name}",
        f"Email: {cv_data.email or 'N/A'}",
        f"Phone: {cv_data.phone or 'N/A'}",
        f"Location: {cv_data.location or 'N/A'}",
    ]

    if cv_data.summary:
        lines.append(f"\nSummary:\n{cv_data.summary}")

    if cv_data.experience:
        lines.append("\nExperience:")
        for exp in cv_data.experience:
            lines.append(
                f"  - {exp.position} at {exp.company} ({exp.start_date or 'N/A'} - {exp.end_date or 'N/A'})"
            )
            if exp.description:
                lines.append(f"    {exp.description}")

    if cv_data.education:
        lines.append("\nEducation:")
        for edu in cv_data.education:
            lines.append(
                f"  - {edu.degree} in {edu.field_of_study or 'N/A'} from {edu.institution}"
            )

    if cv_data.skills:
        lines.append("\nSkills:")
        for skill in cv_data.skills:
            lines.append(f"  - {skill.name} ({skill.proficiency or 'N/A'})")

    return "\n".join(lines)


def format_hr_feedback(hr_feedback: HRFeedback, include_extraction_note: bool = False) -> str:
    """Format HR feedback for prompt."""
    lines = [
        f"Decision: {hr_feedback.decision.value}",
    ]

    if hr_feedback.notes:
        lines.append(f"\nHR Notes and Evaluation:\n{hr_feedback.notes}")
        if include_extraction_note:
            lines.append(
                "\nIMPORTANT: Extract and identify candidate's strengths and areas for improvement from the HR notes above."
            )

    if hr_feedback.position_applied:
        lines.append(f"\nPosition Applied: {hr_feedback.position_applied}")

    if hr_feedback.missing_requirements:
        lines.append(f"\nMissing Requirements: {', '.join(hr_feedback.missing_requirements)}")

    return "\n".join(lines)


def format_job_offer(job_offer: JobOffer) -> str:
    """Format job offer for prompt."""
    lines = [
        f"Job Title: {job_offer.title}",
    ]

    if job_offer.company:
        lines.append(f"Company: {job_offer.company}")

    if job_offer.location:
        lines.append(f"Location: {job_offer.location}")

    if job_offer.description:
        lines.append(f"\nJob Description:\n{job_offer.description}")

    return "\n".join(lines)

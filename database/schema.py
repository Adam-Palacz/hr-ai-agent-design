"""Database schema: enums and model classes."""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class CandidateStatus(str, Enum):
    """Candidate application status."""

    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RecruitmentStage(str, Enum):
    """Recruitment process stages."""

    INITIAL_SCREENING = "initial_screening"
    HR_INTERVIEW = "hr_interview"
    TECHNICAL_ASSESSMENT = "technical_assessment"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"


class TicketStatus(str, Enum):
    """Ticket status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    """Ticket priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketDepartment(str, Enum):
    """Ticket department."""

    IOD = "IOD"
    HR = "HR"
    IT = "IT"
    ADMIN = "ADMIN"


class Candidate:
    """Candidate model."""

    def __init__(
        self,
        id: Optional[int] = None,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        position_id: Optional[int] = None,
        status: CandidateStatus = CandidateStatus.IN_PROGRESS,
        stage: RecruitmentStage = RecruitmentStage.INITIAL_SCREENING,
        cv_path: Optional[str] = None,
        consent_for_other_positions: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.position_id = position_id
        self.status = status
        self.stage = stage
        self.cv_path = cv_path
        self.consent_for_other_positions = bool(consent_for_other_positions)
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "position_id": self.position_id,
            "status": (
                self.status.value if isinstance(self.status, CandidateStatus) else str(self.status)
            ),
            "stage": (
                self.stage.value if isinstance(self.stage, RecruitmentStage) else str(self.stage)
            ),
            "cv_path": self.cv_path,
            "consent_for_other_positions": self.consent_for_other_positions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Position:
    """Job position model."""

    def __init__(
        self,
        id: Optional[int] = None,
        title: str = "",
        company: str = "",
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.title = title
        self.company = company
        self.description = description
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class FeedbackEmail:
    """Feedback email model."""

    def __init__(
        self,
        id: Optional[int] = None,
        candidate_id: int = 0,
        email_content: str = "",
        message_id: Optional[str] = None,
        sent_at: Optional[datetime] = None,
    ):
        self.id = id
        self.candidate_id = candidate_id
        self.email_content = email_content
        self.message_id = message_id
        self.sent_at = sent_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "email_content": self.email_content,
            "message_id": self.message_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class HRNote:
    """HR note model for candidate evaluation."""

    def __init__(
        self,
        id: Optional[int] = None,
        candidate_id: int = 0,
        notes: str = "",
        stage: RecruitmentStage = RecruitmentStage.INITIAL_SCREENING,
        created_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
    ):
        self.id = id
        self.candidate_id = candidate_id
        self.notes = notes
        self.stage = stage if isinstance(stage, RecruitmentStage) else RecruitmentStage(stage)
        self.created_at = created_at or datetime.now()
        self.created_by = created_by

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "notes": self.notes,
            "stage": (
                self.stage.value if isinstance(self.stage, RecruitmentStage) else str(self.stage)
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


class ValidationError:
    """Validation error model."""

    def __init__(
        self,
        id: Optional[int] = None,
        candidate_id: int = 0,
        error_message: str = "",
        feedback_html_content: Optional[str] = None,
        validation_results: Optional[str] = None,
        model_responses_summary: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.candidate_id = candidate_id
        self.error_message = error_message
        self.feedback_html_content = feedback_html_content
        self.validation_results = validation_results
        self.model_responses_summary = model_responses_summary
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "error_message": self.error_message,
            "feedback_html_content": self.feedback_html_content,
            "validation_results": self.validation_results,
            "model_responses_summary": self.model_responses_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Ticket:
    """Ticket model for task management."""

    def __init__(
        self,
        id: Optional[int] = None,
        department: TicketDepartment = TicketDepartment.HR,
        priority: TicketPriority = TicketPriority.MEDIUM,
        status: TicketStatus = TicketStatus.OPEN,
        description: str = "",
        deadline: Optional[datetime] = None,
        related_candidate_id: Optional[int] = None,
        related_email_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.department = department
        self.priority = priority
        self.status = status
        self.description = description
        self.deadline = deadline
        self.related_candidate_id = related_candidate_id
        self.related_email_id = related_email_id
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "department": (
                self.department.value
                if isinstance(self.department, TicketDepartment)
                else str(self.department)
            ),
            "priority": (
                self.priority.value
                if isinstance(self.priority, TicketPriority)
                else str(self.priority)
            ),
            "status": (
                self.status.value if isinstance(self.status, TicketStatus) else str(self.status)
            ),
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "related_candidate_id": self.related_candidate_id,
            "related_email_id": self.related_email_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ModelResponse:
    """Model response tracking model."""

    def __init__(
        self,
        id: Optional[int] = None,
        agent_type: str = "",
        model_name: str = "",
        candidate_id: Optional[int] = None,
        feedback_email_id: Optional[int] = None,
        input_data: Optional[str] = None,
        output_data: Optional[str] = None,
        metadata: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.agent_type = agent_type
        self.model_name = model_name
        self.candidate_id = candidate_id
        self.feedback_email_id = feedback_email_id
        self.input_data = input_data
        self.output_data = output_data
        self.metadata = metadata
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "model_name": self.model_name,
            "candidate_id": self.candidate_id,
            "feedback_email_id": self.feedback_email_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

"""
Database models - re-exports for backward compatibility.

All schema types and CRUD are defined in database.schema, database.db,
and database.* (candidates, positions, feedback_emails, hr_notes,
model_responses, validation_errors, tickets).
"""

from database.schema import (
    Candidate,
    CandidateStatus,
    FeedbackEmail,
    HRNote,
    ModelResponse,
    Position,
    RecruitmentStage,
    Ticket,
    TicketDepartment,
    TicketPriority,
    TicketStatus,
    ValidationError,
)
from database.db import get_db_path, get_db, init_db, clear_database
from database.candidates import (
    get_all_candidates,
    get_candidate_by_email,
    get_candidate_by_id,
    create_candidate,
    update_candidate,
    delete_candidate,
)
from database.positions import (
    get_all_positions,
    get_position_by_id,
    create_position,
    update_position,
    delete_position,
)
from database.feedback_emails import (
    save_feedback_email,
    get_feedback_emails_for_candidate,
    get_all_feedback_emails,
    get_feedback_email_by_message_id,
)
from database.hr_notes import (
    create_hr_note,
    get_hr_notes_for_candidate,
    get_all_hr_notes,
)
from database.model_responses import (
    save_model_response,
    get_model_responses_for_candidate,
    get_all_model_responses,
)
from database.validation_errors import (
    save_validation_error,
    get_validation_errors_for_candidate,
    get_all_validation_errors,
)
from database.tickets import (
    create_ticket,
    get_ticket_by_id,
    get_all_tickets,
    update_ticket,
    delete_ticket,
)

__all__ = [
    "Candidate",
    "CandidateStatus",
    "FeedbackEmail",
    "HRNote",
    "ModelResponse",
    "Position",
    "RecruitmentStage",
    "Ticket",
    "TicketDepartment",
    "TicketPriority",
    "TicketStatus",
    "ValidationError",
    "get_db_path",
    "get_db",
    "init_db",
    "clear_database",
    "get_all_candidates",
    "get_candidate_by_email",
    "get_candidate_by_id",
    "create_candidate",
    "update_candidate",
    "delete_candidate",
    "get_all_positions",
    "get_position_by_id",
    "create_position",
    "update_position",
    "delete_position",
    "save_feedback_email",
    "get_feedback_emails_for_candidate",
    "get_all_feedback_emails",
    "get_feedback_email_by_message_id",
    "create_hr_note",
    "get_hr_notes_for_candidate",
    "get_all_hr_notes",
    "save_model_response",
    "get_model_responses_for_candidate",
    "get_all_model_responses",
    "save_validation_error",
    "get_validation_errors_for_candidate",
    "get_all_validation_errors",
    "create_ticket",
    "get_ticket_by_id",
    "get_all_tickets",
    "update_ticket",
    "delete_ticket",
]

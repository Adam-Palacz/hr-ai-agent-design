"""Database models and initialization."""
from .models import (
    init_db, get_db, Candidate, Position, FeedbackEmail, HRNote, ModelResponse, ValidationError,
    get_all_candidates, get_candidate_by_id, get_candidate_by_email, create_candidate, update_candidate,
    get_all_positions, get_position_by_id, create_position, update_position, delete_position,
    save_feedback_email, get_feedback_emails_for_candidate, get_all_feedback_emails,
    get_feedback_email_by_message_id,
    save_model_response, get_model_responses_for_candidate, get_all_model_responses,
    create_hr_note, get_hr_notes_for_candidate, get_all_hr_notes,
    save_validation_error, get_validation_errors_for_candidate, get_all_validation_errors,
    CandidateStatus, RecruitmentStage
)

__all__ = [
    'init_db', 'get_db', 'Candidate', 'Position', 'FeedbackEmail', 'HRNote', 'ModelResponse', 'ValidationError',
    'get_all_candidates', 'get_candidate_by_id', 'get_candidate_by_email', 'create_candidate', 'update_candidate',
    'get_all_positions', 'get_position_by_id', 'create_position', 'update_position', 'delete_position',
    'save_feedback_email', 'get_feedback_emails_for_candidate', 'get_all_feedback_emails',
    'get_feedback_email_by_message_id',
    'save_model_response', 'get_model_responses_for_candidate', 'get_all_model_responses',
    'create_hr_note', 'get_hr_notes_for_candidate', 'get_all_hr_notes',
    'save_validation_error', 'get_validation_errors_for_candidate', 'get_all_validation_errors',
    'CandidateStatus', 'RecruitmentStage'
]


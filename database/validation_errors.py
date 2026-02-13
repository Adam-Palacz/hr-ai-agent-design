"""Validation error CRUD operations."""

from datetime import datetime
from typing import List, Optional

from database.db import get_db
from database.schema import ValidationError


def save_validation_error(
    candidate_id: int,
    error_message: str,
    feedback_html_content: Optional[str] = None,
    validation_results: Optional[str] = None,
    model_responses_summary: Optional[str] = None,
) -> ValidationError:
    """Save validation error to database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO validation_errors (candidate_id, error_message, feedback_html_content, validation_results, model_responses_summary)
        VALUES (?, ?, ?, ?, ?)
    """,
        (
            candidate_id,
            error_message,
            feedback_html_content,
            validation_results,
            model_responses_summary,
        ),
    )
    error_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ValidationError(
        id=error_id,
        candidate_id=candidate_id,
        error_message=error_message,
        feedback_html_content=feedback_html_content,
        validation_results=validation_results,
        model_responses_summary=model_responses_summary,
        created_at=datetime.now(),
    )


def get_validation_errors_for_candidate(candidate_id: int) -> List[ValidationError]:
    """Get all validation errors for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM validation_errors WHERE candidate_id = ? ORDER BY created_at DESC",
        (candidate_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        ValidationError(
            id=row["id"],
            candidate_id=row["candidate_id"],
            error_message=row["error_message"],
            feedback_html_content=row["feedback_html_content"],
            validation_results=row["validation_results"],
            model_responses_summary=row["model_responses_summary"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
        for row in rows
    ]


def get_all_validation_errors() -> List[ValidationError]:
    """Get all validation errors from database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM validation_errors ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        ValidationError(
            id=row["id"],
            candidate_id=row["candidate_id"],
            error_message=row["error_message"],
            feedback_html_content=row["feedback_html_content"],
            validation_results=row["validation_results"],
            model_responses_summary=row["model_responses_summary"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
        for row in rows
    ]

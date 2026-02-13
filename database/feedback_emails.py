"""Feedback email CRUD operations."""

from datetime import datetime
from typing import List, Optional

from database.db import get_db
from database.schema import FeedbackEmail


def save_feedback_email(
    candidate_id: int, email_content: str, message_id: Optional[str] = None
) -> FeedbackEmail:
    """Save feedback email to database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO feedback_emails (candidate_id, email_content, message_id)
        VALUES (?, ?, ?)
    """,
        (candidate_id, email_content, message_id),
    )
    email_id = cursor.lastrowid
    conn.commit()
    conn.close()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedback_emails WHERE id = ?", (email_id,))
    row = cursor.fetchone()
    conn.close()
    return FeedbackEmail(
        id=row["id"],
        candidate_id=row["candidate_id"],
        email_content=row["email_content"],
        message_id=row["message_id"] if "message_id" in row.keys() else None,
        sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
    )


def get_feedback_emails_for_candidate(candidate_id: int) -> List[FeedbackEmail]:
    """Get all feedback emails for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM feedback_emails WHERE candidate_id = ? ORDER BY sent_at DESC",
        (candidate_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        FeedbackEmail(
            id=row["id"],
            candidate_id=row["candidate_id"],
            email_content=row["email_content"],
            message_id=row["message_id"] if "message_id" in row.keys() else None,
            sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
        )
        for row in rows
    ]


def get_all_feedback_emails() -> List[FeedbackEmail]:
    """Get all feedback emails from database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedback_emails ORDER BY sent_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        FeedbackEmail(
            id=row["id"],
            candidate_id=row["candidate_id"],
            email_content=row["email_content"],
            message_id=row["message_id"] if "message_id" in row.keys() else None,
            sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
        )
        for row in rows
    ]


def get_feedback_email_by_message_id(message_id: str) -> Optional[FeedbackEmail]:
    """Get feedback email by Message-ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM feedback_emails WHERE message_id = ?", (message_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return FeedbackEmail(
        id=row["id"],
        candidate_id=row["candidate_id"],
        email_content=row["email_content"],
        message_id=row["message_id"] if "message_id" in row.keys() else None,
        sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
    )

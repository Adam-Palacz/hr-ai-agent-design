"""Candidate CRUD operations."""

from datetime import datetime
from typing import List, Optional

from database.db import get_db
from database.schema import Candidate, CandidateStatus, RecruitmentStage


def _row_to_candidate(row) -> Candidate:
    """Convert DB row to Candidate."""
    status = CandidateStatus(row["status"]) if row["status"] else CandidateStatus.IN_PROGRESS
    stage = RecruitmentStage(row["stage"]) if row["stage"] else RecruitmentStage.INITIAL_SCREENING
    consent_value = False
    if (
        "consent_for_other_positions" in row.keys()
        and row["consent_for_other_positions"] is not None
    ):
        consent_value = bool(row["consent_for_other_positions"])
    return Candidate(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        position_id=row["position_id"],
        status=status,
        stage=stage,
        cv_path=row["cv_path"],
        consent_for_other_positions=consent_value,
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
    )


def get_all_candidates() -> List[Candidate]:
    """Get all candidates with their positions."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_candidate(row) for row in rows]


def get_candidate_by_email(email: str) -> Optional[Candidate]:
    """Get candidate by email address."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_candidate(row)


def get_candidate_by_id(candidate_id: int) -> Optional[Candidate]:
    """Get candidate by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_candidate(row)


def create_candidate(
    first_name: str,
    last_name: str,
    email: str,
    position_id: Optional[int] = None,
    status: CandidateStatus = CandidateStatus.IN_PROGRESS,
    stage: RecruitmentStage = RecruitmentStage.INITIAL_SCREENING,
    cv_path: Optional[str] = None,
    consent_for_other_positions: Optional[bool] = None,
) -> Candidate:
    """Create a new candidate."""
    conn = get_db()
    cursor = conn.cursor()
    consent_int = 1 if consent_for_other_positions else 0
    cursor.execute(
        """
        INSERT INTO candidates (first_name, last_name, email, position_id, status, stage, cv_path, consent_for_other_positions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            first_name,
            last_name,
            email,
            position_id,
            status.value,
            stage.value,
            cv_path,
            consent_int,
        ),
    )
    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_candidate_by_id(candidate_id)


def update_candidate(
    candidate_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    position_id: Optional[int] = None,
    status: Optional[CandidateStatus] = None,
    stage: Optional[RecruitmentStage] = None,
    cv_path: Optional[str] = None,
    consent_for_other_positions: Optional[bool] = None,
) -> Optional[Candidate]:
    """Update candidate information."""
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    values = []
    if first_name is not None:
        updates.append("first_name = ?")
        values.append(first_name)
    if last_name is not None:
        updates.append("last_name = ?")
        values.append(last_name)
    if email is not None:
        updates.append("email = ?")
        values.append(email)
    if position_id is not None:
        updates.append("position_id = ?")
        values.append(position_id)
    if status is not None:
        updates.append("status = ?")
        values.append(status.value if isinstance(status, CandidateStatus) else str(status))
    if stage is not None:
        updates.append("stage = ?")
        values.append(stage.value if isinstance(stage, RecruitmentStage) else str(stage))
    if cv_path is not None:
        updates.append("cv_path = ?")
        values.append(cv_path)
    if consent_for_other_positions is not None:
        updates.append("consent_for_other_positions = ?")
        values.append(1 if consent_for_other_positions else 0)
    if not updates:
        conn.close()
        return get_candidate_by_id(candidate_id)
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(candidate_id)
    cursor.execute(f'UPDATE candidates SET {", ".join(updates)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    return get_candidate_by_id(candidate_id)


def delete_candidate(candidate_id: int) -> bool:
    """Delete a candidate and all related records."""
    from core.logger import logger

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM feedback_emails WHERE candidate_id = ?", (candidate_id,))
        cursor.execute("DELETE FROM hr_notes WHERE candidate_id = ?", (candidate_id,))
        cursor.execute("DELETE FROM model_responses WHERE candidate_id = ?", (candidate_id,))
        cursor.execute("DELETE FROM validation_errors WHERE candidate_id = ?", (candidate_id,))
        cursor.execute(
            "UPDATE tickets SET related_candidate_id = NULL WHERE related_candidate_id = ?",
            (candidate_id,),
        )
        cursor.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        if deleted:
            logger.info(f"Deleted candidate {candidate_id} and all related records")
        return deleted
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error deleting candidate {candidate_id}: {str(e)}")
        return False

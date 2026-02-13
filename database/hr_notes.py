"""HR notes CRUD operations."""

from datetime import datetime
from typing import List, Optional

from database.db import get_db
from database.schema import HRNote, RecruitmentStage


def create_hr_note(
    candidate_id: int, notes: str, stage: RecruitmentStage, created_by: Optional[str] = None
) -> HRNote:
    """Create a new HR note for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    stage_value = stage.value if isinstance(stage, RecruitmentStage) else str(stage)
    cursor.execute(
        """
        INSERT INTO hr_notes (candidate_id, notes, stage, created_by)
        VALUES (?, ?, ?, ?)
    """,
        (candidate_id, notes, stage_value, created_by),
    )
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return HRNote(
        id=note_id, candidate_id=candidate_id, notes=notes, stage=stage, created_by=created_by
    )


def get_hr_notes_for_candidate(candidate_id: int) -> List[HRNote]:
    """Get all HR notes for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM hr_notes WHERE candidate_id = ? ORDER BY created_at DESC", (candidate_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        HRNote(
            id=row["id"],
            candidate_id=row["candidate_id"],
            notes=row["notes"],
            stage=RecruitmentStage(row["stage"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            created_by=row["created_by"] if "created_by" in row.keys() else None,
        )
        for row in rows
    ]


def get_all_hr_notes() -> List[HRNote]:
    """Get all HR notes from database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hr_notes ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        HRNote(
            id=row["id"],
            candidate_id=row["candidate_id"],
            notes=row["notes"],
            stage=RecruitmentStage(row["stage"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            created_by=row["created_by"] if "created_by" in row.keys() else None,
        )
        for row in rows
    ]

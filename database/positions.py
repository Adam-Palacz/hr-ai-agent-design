"""Position CRUD operations."""

from datetime import datetime
from typing import List, Optional

from database.db import get_db
from database.schema import Position


def get_all_positions() -> List[Position]:
    """Get all positions."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM positions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        Position(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            description=row["description"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
        for row in rows
    ]


def get_position_by_id(position_id: int) -> Optional[Position]:
    """Get position by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return Position(
        id=row["id"],
        title=row["title"],
        company=row["company"],
        description=row["description"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
    )


def create_position(title: str, company: str, description: Optional[str] = None) -> Position:
    """Create a new position."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO positions (title, company, description)
        VALUES (?, ?, ?)
    """,
        (title, company, description),
    )
    position_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_position_by_id(position_id)


def update_position(
    position_id: int,
    title: Optional[str] = None,
    company: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[Position]:
    """Update position information."""
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    values = []
    if title is not None:
        updates.append("title = ?")
        values.append(title)
    if company is not None:
        updates.append("company = ?")
        values.append(company)
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if not updates:
        conn.close()
        return get_position_by_id(position_id)
    values.append(position_id)
    cursor.execute(f'UPDATE positions SET {", ".join(updates)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    return get_position_by_id(position_id)


def delete_position(position_id: int) -> bool:
    """Delete a position."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

"""Ticket CRUD operations."""

from datetime import datetime
from typing import List, Optional

from database.db import get_db
from database.schema import (
    Ticket,
    TicketDepartment,
    TicketPriority,
    TicketStatus,
)


def create_ticket(
    department: TicketDepartment,
    priority: TicketPriority,
    description: str,
    deadline: Optional[datetime] = None,
    related_candidate_id: Optional[int] = None,
    related_email_id: Optional[str] = None,
    status: TicketStatus = TicketStatus.OPEN,
) -> Ticket:
    """Create a new ticket."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO tickets (department, priority, status, description, deadline, related_candidate_id, related_email_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            department.value if isinstance(department, TicketDepartment) else str(department),
            priority.value if isinstance(priority, TicketPriority) else str(priority),
            status.value if isinstance(status, TicketStatus) else str(status),
            description,
            deadline.isoformat() if deadline else None,
            related_candidate_id,
            related_email_id,
        ),
    )
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return Ticket(
        id=ticket_id,
        department=department,
        priority=priority,
        status=status,
        description=description,
        deadline=deadline,
        related_candidate_id=related_candidate_id,
        related_email_id=related_email_id,
    )


def get_ticket_by_id(ticket_id: int) -> Optional[Ticket]:
    """Get ticket by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return Ticket(
        id=row["id"],
        department=TicketDepartment(row["department"]),
        priority=TicketPriority(row["priority"]),
        status=TicketStatus(row["status"]),
        description=row["description"],
        deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
        related_candidate_id=row["related_candidate_id"],
        related_email_id=row["related_email_id"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
    )


def get_all_tickets() -> List[Ticket]:
    """Get all tickets."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        Ticket(
            id=row["id"],
            department=TicketDepartment(row["department"]),
            priority=TicketPriority(row["priority"]),
            status=TicketStatus(row["status"]),
            description=row["description"],
            deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
            related_candidate_id=row["related_candidate_id"],
            related_email_id=row["related_email_id"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
        for row in rows
    ]


def update_ticket(
    ticket_id: int,
    department: Optional[TicketDepartment] = None,
    priority: Optional[TicketPriority] = None,
    status: Optional[TicketStatus] = None,
    description: Optional[str] = None,
    deadline: Optional[datetime] = None,
) -> bool:
    """Update ticket."""
    conn = get_db()
    cursor = conn.cursor()
    updates = []
    values = []
    if department is not None:
        updates.append("department = ?")
        values.append(
            department.value if isinstance(department, TicketDepartment) else str(department)
        )
    if priority is not None:
        updates.append("priority = ?")
        values.append(priority.value if isinstance(priority, TicketPriority) else str(priority))
    if status is not None:
        updates.append("status = ?")
        values.append(status.value if isinstance(status, TicketStatus) else str(status))
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    if deadline is not None:
        updates.append("deadline = ?")
        values.append(deadline.isoformat())
    if not updates:
        conn.close()
        return False
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(ticket_id)
    cursor.execute(f'UPDATE tickets SET {", ".join(updates)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def delete_ticket(ticket_id: int) -> bool:
    """Delete ticket."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

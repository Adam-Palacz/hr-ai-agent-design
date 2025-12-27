"""Database models for candidates, positions, and feedback."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from core.logger import logger


class CandidateStatus(str, Enum):
    """Candidate application status."""
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RecruitmentStage(str, Enum):
    """Recruitment process stages."""
    INITIAL_SCREENING = "initial_screening"  # Pierwsza selekcja
    HR_INTERVIEW = "hr_interview"  # Rozmowa z HR
    TECHNICAL_ASSESSMENT = "technical_assessment"  # Weryfikacja wiedzy
    FINAL_INTERVIEW = "final_interview"  # Rozmowa końcowa
    OFFER = "offer"  # Oferta


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
    
    def __init__(self, 
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
                 updated_at: Optional[datetime] = None):
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
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'position_id': self.position_id,
            'status': self.status.value if isinstance(self.status, CandidateStatus) else str(self.status),
            'stage': self.stage.value if isinstance(self.stage, RecruitmentStage) else str(self.stage),
            'cv_path': self.cv_path,
            'consent_for_other_positions': self.consent_for_other_positions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Position:
    """Job position model."""
    
    def __init__(self,
                 id: Optional[int] = None,
                 title: str = "",
                 company: str = "",
                 description: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.title = title
        self.company = company
        self.description = description
        self.created_at = created_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FeedbackEmail:
    """Feedback email model."""
    
    def __init__(self,
                 id: Optional[int] = None,
                 candidate_id: int = 0,
                 email_content: str = "",
                 message_id: Optional[str] = None,
                 sent_at: Optional[datetime] = None):
        self.id = id
        self.candidate_id = candidate_id
        self.email_content = email_content
        self.message_id = message_id
        self.sent_at = sent_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'email_content': self.email_content,
            'message_id': self.message_id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }


class HRNote:
    """HR note model for candidate evaluation."""
    
    def __init__(self,
                 id: Optional[int] = None,
                 candidate_id: int = 0,
                 notes: str = "",
                 stage: RecruitmentStage = RecruitmentStage.INITIAL_SCREENING,
                 created_at: Optional[datetime] = None,
                 created_by: Optional[str] = None):
        self.id = id
        self.candidate_id = candidate_id
        self.notes = notes
        self.stage = stage if isinstance(stage, RecruitmentStage) else RecruitmentStage(stage)
        self.created_at = created_at or datetime.now()
        self.created_by = created_by
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'notes': self.notes,
            'stage': self.stage.value if isinstance(self.stage, RecruitmentStage) else str(self.stage),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }


class ValidationError:
    """Validation error model."""
    
    def __init__(self,
                 id: Optional[int] = None,
                 candidate_id: int = 0,
                 error_message: str = "",
                 feedback_html_content: Optional[str] = None,
                 validation_results: Optional[str] = None,
                 model_responses_summary: Optional[str] = None,
                 created_at: Optional[datetime] = None):
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
            'id': self.id,
            'candidate_id': self.candidate_id,
            'error_message': self.error_message,
            'feedback_html_content': self.feedback_html_content,
            'validation_results': self.validation_results,
            'model_responses_summary': self.model_responses_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Ticket:
    """Ticket model for task management."""
    
    def __init__(self,
                 id: Optional[int] = None,
                 department: TicketDepartment = TicketDepartment.HR,
                 priority: TicketPriority = TicketPriority.MEDIUM,
                 status: TicketStatus = TicketStatus.OPEN,
                 description: str = "",
                 deadline: Optional[datetime] = None,
                 related_candidate_id: Optional[int] = None,
                 related_email_id: Optional[str] = None,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None):
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
            'id': self.id,
            'department': self.department.value if isinstance(self.department, TicketDepartment) else str(self.department),
            'priority': self.priority.value if isinstance(self.priority, TicketPriority) else str(self.priority),
            'status': self.status.value if isinstance(self.status, TicketStatus) else str(self.status),
            'description': self.description,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'related_candidate_id': self.related_candidate_id,
            'related_email_id': self.related_email_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ModelResponse:
    """Model response tracking model."""
    
    def __init__(self,
                 id: Optional[int] = None,
                 agent_type: str = "",
                 model_name: str = "",
                 candidate_id: Optional[int] = None,
                 feedback_email_id: Optional[int] = None,
                 input_data: Optional[str] = None,
                 output_data: Optional[str] = None,
                 metadata: Optional[str] = None,
                 created_at: Optional[datetime] = None):
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
            'id': self.id,
            'agent_type': self.agent_type,
            'model_name': self.model_name,
            'candidate_id': self.candidate_id,
            'feedback_email_id': self.feedback_email_id,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


def get_db_path() -> Path:
    """Get database file path."""
    db_dir = Path('data')
    db_dir.mkdir(exist_ok=True)
    return db_dir / 'hr_database.db'


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with tables."""
    db_path = get_db_path()
    conn = get_db()
    cursor = conn.cursor()
    
    # Create positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create candidates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            position_id INTEGER,
            status TEXT NOT NULL DEFAULT 'in_progress',
            stage TEXT NOT NULL DEFAULT 'initial_screening',
            cv_path TEXT,
            consent_for_other_positions INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (position_id) REFERENCES positions(id)
        )
    ''')
    
    # Add consent_for_other_positions column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE candidates ADD COLUMN consent_for_other_positions INTEGER DEFAULT NULL')
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass

    # Normalize existing data: no "unknown" state in UI -> treat NULL as "Nie" (0)
    try:
        cursor.execute('UPDATE candidates SET consent_for_other_positions = 0 WHERE consent_for_other_positions IS NULL')
    except sqlite3.OperationalError:
        # Column may not exist yet in some edge cases; ignore
        pass
    
    # Create feedback_emails table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            email_content TEXT NOT NULL,
            message_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')
    
    # Add message_id column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE feedback_emails ADD COLUMN message_id TEXT')
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
    # Create hr_notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hr_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            notes TEXT NOT NULL,
            stage TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')
    
    # Create model_responses table for tracking LLM responses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_type TEXT NOT NULL,
            model_name TEXT NOT NULL,
            candidate_id INTEGER,
            feedback_email_id INTEGER,
            input_data TEXT,
            output_data TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            FOREIGN KEY (feedback_email_id) REFERENCES feedback_emails(id)
        )
    ''')
    
    # Create validation_errors table for tracking validation failures
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS validation_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            error_message TEXT NOT NULL,
            feedback_html_content TEXT,
            validation_results TEXT,
            model_responses_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')
    
    # Create tickets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            description TEXT NOT NULL,
            deadline TIMESTAMP,
            related_candidate_id INTEGER,
            related_email_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (related_candidate_id) REFERENCES candidates(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at: {db_path}")


def clear_database(reset_autoincrement: bool = True) -> None:
    """
    Clear (DELETE) all rows from application tables WITHOUT dropping tables.

    This is meant for dev/demo usage to quickly reset the database content while
    keeping the schema intact.

    Args:
        reset_autoincrement: If True, also resets SQLite AUTOINCREMENT counters
            by clearing rows from sqlite_sequence for known tables.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Ensure schema exists
    init_db()

    # FK-safe delete order (children -> parents)
    tables_in_delete_order = [
        "model_responses",
        "validation_errors",
        "hr_notes",
        "feedback_emails",
        "tickets",
        "candidates",
        "positions",
    ]

    try:
        # Temporarily disable FK checks to avoid issues with partial/inconsistent data.
        cursor.execute("PRAGMA foreign_keys = OFF;")
        for table in tables_in_delete_order:
            cursor.execute(f"DELETE FROM {table};")

        if reset_autoincrement:
            # sqlite_sequence exists only if any table uses AUTOINCREMENT.
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';"
            )
            if cursor.fetchone():
                for table in tables_in_delete_order:
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?;", (table,))

        conn.commit()
        logger.info("Database cleared (tables kept).")
    finally:
        try:
            cursor.execute("PRAGMA foreign_keys = ON;")
        except Exception:
            pass
        conn.close()


def get_all_candidates() -> List[Candidate]:
    """Get all candidates with their positions."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM candidates ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    candidates = []
    for row in rows:
        status = CandidateStatus(row['status']) if row['status'] else CandidateStatus.IN_PROGRESS
        stage = RecruitmentStage(row['stage']) if row['stage'] else RecruitmentStage.INITIAL_SCREENING
        
        # Treat NULL as False ("Nie") to avoid tri-state
        consent_value = False
        if 'consent_for_other_positions' in row.keys() and row['consent_for_other_positions'] is not None:
            consent_value = bool(row['consent_for_other_positions'])
        
        candidates.append(Candidate(
            id=row['id'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            email=row['email'],
            position_id=row['position_id'],
            status=status,
            stage=stage,
            cv_path=row['cv_path'],
            consent_for_other_positions=consent_value,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        ))
    
    return candidates


def get_candidate_by_email(email: str) -> Optional[Candidate]:
    """Get candidate by email address."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    status = CandidateStatus(row['status']) if row['status'] else CandidateStatus.IN_PROGRESS
    stage = RecruitmentStage(row['stage']) if row['stage'] else RecruitmentStage.INITIAL_SCREENING
    
    consent_value = False
    if 'consent_for_other_positions' in row.keys() and row['consent_for_other_positions'] is not None:
        consent_value = bool(row['consent_for_other_positions'])
    
    return Candidate(
        id=row['id'],
        first_name=row['first_name'],
        last_name=row['last_name'],
        email=row['email'],
        position_id=row['position_id'],
        status=status,
        stage=stage,
        cv_path=row['cv_path'],
        consent_for_other_positions=consent_value,
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
    )


def get_candidate_by_id(candidate_id: int) -> Optional[Candidate]:
    """Get candidate by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM candidates WHERE id = ?', (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    status = CandidateStatus(row['status']) if row['status'] else CandidateStatus.IN_PROGRESS
    stage = RecruitmentStage(row['stage']) if row['stage'] else RecruitmentStage.INITIAL_SCREENING
    
    consent_value = False
    if 'consent_for_other_positions' in row.keys() and row['consent_for_other_positions'] is not None:
        consent_value = bool(row['consent_for_other_positions'])
    
    return Candidate(
        id=row['id'],
        first_name=row['first_name'],
        last_name=row['last_name'],
        email=row['email'],
        position_id=row['position_id'],
        status=status,
        stage=stage,
        cv_path=row['cv_path'],
        consent_for_other_positions=consent_value,
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
    )


def create_candidate(
    first_name: str,
    last_name: str,
    email: str,
    position_id: Optional[int] = None,
    status: CandidateStatus = CandidateStatus.IN_PROGRESS,
    stage: RecruitmentStage = RecruitmentStage.INITIAL_SCREENING,
    cv_path: Optional[str] = None,
    consent_for_other_positions: Optional[bool] = None
) -> Candidate:
    """Create a new candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    # No tri-state: treat None as False ("Nie")
    consent_int = 1 if consent_for_other_positions else 0
    
    cursor.execute('''
        INSERT INTO candidates (first_name, last_name, email, position_id, status, stage, cv_path, consent_for_other_positions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (first_name, last_name, email, position_id, status.value, stage.value, cv_path, consent_int))
    
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
    consent_for_other_positions: Optional[bool] = None
) -> Optional[Candidate]:
    """Update candidate information."""
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if first_name is not None:
        updates.append('first_name = ?')
        values.append(first_name)
    if last_name is not None:
        updates.append('last_name = ?')
        values.append(last_name)
    if email is not None:
        updates.append('email = ?')
        values.append(email)
    if position_id is not None:
        updates.append('position_id = ?')
        values.append(position_id)
    if status is not None:
        updates.append('status = ?')
        values.append(status.value if isinstance(status, CandidateStatus) else str(status))
    if stage is not None:
        updates.append('stage = ?')
        values.append(stage.value if isinstance(stage, RecruitmentStage) else str(stage))
    if cv_path is not None:
        updates.append('cv_path = ?')
        values.append(cv_path)
    if consent_for_other_positions is not None:
        updates.append('consent_for_other_positions = ?')
        values.append(1 if consent_for_other_positions else 0)
    
    if not updates:
        conn.close()
        return get_candidate_by_id(candidate_id)
    
    updates.append('updated_at = CURRENT_TIMESTAMP')
    values.append(candidate_id)
    
    cursor.execute(f'UPDATE candidates SET {", ".join(updates)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    
    return get_candidate_by_id(candidate_id)


def get_all_positions() -> List[Position]:
    """Get all positions."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM positions ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    positions = []
    for row in rows:
        positions.append(Position(
            id=row['id'],
            title=row['title'],
            company=row['company'],
            description=row['description'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        ))
    
    return positions


def get_position_by_id(position_id: int) -> Optional[Position]:
    """Get position by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM positions WHERE id = ?', (position_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return Position(
        id=row['id'],
        title=row['title'],
        company=row['company'],
        description=row['description'],
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
    )


def create_position(title: str, company: str, description: Optional[str] = None) -> Position:
    """Create a new position."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO positions (title, company, description)
        VALUES (?, ?, ?)
    ''', (title, company, description))
    
    position_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return get_position_by_id(position_id)


def update_position(position_id: int, title: Optional[str] = None, company: Optional[str] = None, description: Optional[str] = None) -> Optional[Position]:
    """Update position information."""
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if title is not None:
        updates.append('title = ?')
        values.append(title)
    if company is not None:
        updates.append('company = ?')
        values.append(company)
    if description is not None:
        updates.append('description = ?')
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
    
    cursor.execute('DELETE FROM positions WHERE id = ?', (position_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    
    return deleted


def save_feedback_email(candidate_id: int, email_content: str, message_id: Optional[str] = None) -> FeedbackEmail:
    """Save feedback email to database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO feedback_emails (candidate_id, email_content, message_id)
        VALUES (?, ?, ?)
    ''', (candidate_id, email_content, message_id))
    
    email_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM feedback_emails WHERE id = ?', (email_id,))
    row = cursor.fetchone()
    conn.close()
    
    return FeedbackEmail(
        id=row['id'],
        candidate_id=row['candidate_id'],
        email_content=row['email_content'],
        message_id=row['message_id'] if 'message_id' in row.keys() else None,
        sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None
    )


def get_feedback_emails_for_candidate(candidate_id: int) -> List[FeedbackEmail]:
    """Get all feedback emails for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM feedback_emails WHERE candidate_id = ? ORDER BY sent_at DESC', (candidate_id,))
    rows = cursor.fetchall()
    conn.close()
    
    emails = []
    for row in rows:
        emails.append(FeedbackEmail(
            id=row['id'],
            candidate_id=row['candidate_id'],
            email_content=row['email_content'],
            message_id=row['message_id'] if 'message_id' in row.keys() else None,
            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None
        ))
    
    return emails


def get_all_feedback_emails() -> List[FeedbackEmail]:
    """Get all feedback emails from database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM feedback_emails ORDER BY sent_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    emails = []
    for row in rows:
        emails.append(FeedbackEmail(
            id=row['id'],
            candidate_id=row['candidate_id'],
            email_content=row['email_content'],
            message_id=row['message_id'] if 'message_id' in row.keys() else None,
            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None
        ))
    
    return emails


def get_feedback_email_by_message_id(message_id: str) -> Optional[FeedbackEmail]:
    """Get feedback email by Message-ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM feedback_emails WHERE message_id = ?', (message_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return FeedbackEmail(
        id=row['id'],
        candidate_id=row['candidate_id'],
        email_content=row['email_content'],
        message_id=row['message_id'] if 'message_id' in row.keys() else None,
        sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None
    )


def create_hr_note(candidate_id: int, notes: str, stage: RecruitmentStage, created_by: Optional[str] = None) -> HRNote:
    """Create a new HR note for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    stage_value = stage.value if isinstance(stage, RecruitmentStage) else str(stage)
    
    cursor.execute('''
        INSERT INTO hr_notes (candidate_id, notes, stage, created_by)
        VALUES (?, ?, ?, ?)
    ''', (candidate_id, notes, stage_value, created_by))
    
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return HRNote(
        id=note_id,
        candidate_id=candidate_id,
        notes=notes,
        stage=stage,
        created_by=created_by
    )


def get_hr_notes_for_candidate(candidate_id: int) -> List[HRNote]:
    """Get all HR notes for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM hr_notes WHERE candidate_id = ? ORDER BY created_at DESC', (candidate_id,))
    rows = cursor.fetchall()
    conn.close()
    
    notes = []
    for row in rows:
        notes.append(HRNote(
            id=row['id'],
            candidate_id=row['candidate_id'],
            notes=row['notes'],
            stage=RecruitmentStage(row['stage']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            created_by=row['created_by'] if 'created_by' in row.keys() else None
        ))
    
    return notes


def get_all_hr_notes() -> List[HRNote]:
    """Get all HR notes from database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM hr_notes ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    notes = []
    for row in rows:
        notes.append(HRNote(
            id=row['id'],
            candidate_id=row['candidate_id'],
            notes=row['notes'],
            stage=RecruitmentStage(row['stage']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            created_by=row['created_by'] if 'created_by' in row.keys() else None
        ))
    
    return notes


def save_model_response(
    agent_type: str,
    model_name: str,
    input_data: Optional[Any] = None,
    output_data: Optional[Any] = None,
    candidate_id: Optional[int] = None,
    feedback_email_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ModelResponse:
    """
    Save model response to database.
    
    Args:
        agent_type: Type of agent (cv_parser, feedback_generator, validator, corrector)
        model_name: Name of the model used
        input_data: Input data (will be serialized to JSON if dict/list)
        output_data: Output data (will be serialized to JSON if dict/list)
        candidate_id: Optional candidate ID
        feedback_email_id: Optional feedback email ID
        metadata: Optional metadata dictionary (will be serialized to JSON)
        
    Returns:
        ModelResponse object
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Serialize input_data
    input_str = None
    if input_data is not None:
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data, ensure_ascii=False, indent=2)
        else:
            input_str = str(input_data)
    
    # Serialize output_data
    output_str = None
    if output_data is not None:
        if isinstance(output_data, (dict, list)):
            output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        else:
            output_str = str(output_data)
    
    # Serialize metadata
    metadata_str = None
    if metadata:
        metadata_str = json.dumps(metadata, ensure_ascii=False, indent=2)
    
    cursor.execute('''
        INSERT INTO model_responses (agent_type, model_name, candidate_id, feedback_email_id, input_data, output_data, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (agent_type, model_name, candidate_id, feedback_email_id, input_str, output_str, metadata_str))
    
    response_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return ModelResponse(
        id=response_id,
        agent_type=agent_type,
        model_name=model_name,
        candidate_id=candidate_id,
        feedback_email_id=feedback_email_id,
        input_data=input_str,
        output_data=output_str,
        metadata=metadata_str,
        created_at=datetime.now()
    )


def get_model_responses_for_candidate(candidate_id: int) -> List[ModelResponse]:
    """Get all model responses for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM model_responses WHERE candidate_id = ? ORDER BY created_at DESC', (candidate_id,))
    rows = cursor.fetchall()
    conn.close()
    
    responses = []
    for row in rows:
        responses.append(ModelResponse(
            id=row['id'],
            agent_type=row['agent_type'],
            model_name=row['model_name'],
            candidate_id=row['candidate_id'],
            feedback_email_id=row['feedback_email_id'] if 'feedback_email_id' in row.keys() else None,
            input_data=row['input_data'],
            output_data=row['output_data'],
            metadata=row['metadata'] if 'metadata' in row.keys() else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        ))
    
    return responses


def get_all_model_responses() -> List[ModelResponse]:
    """Get all model responses from database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM model_responses ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    responses = []
    for row in rows:
        responses.append(ModelResponse(
            id=row['id'],
            agent_type=row['agent_type'],
            model_name=row['model_name'],
            candidate_id=row['candidate_id'],
            feedback_email_id=row['feedback_email_id'] if 'feedback_email_id' in row.keys() else None,
            input_data=row['input_data'],
            output_data=row['output_data'],
            metadata=row['metadata'] if 'metadata' in row.keys() else None,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        ))
    
    return responses


def save_validation_error(
    candidate_id: int,
    error_message: str,
    feedback_html_content: Optional[str] = None,
    validation_results: Optional[str] = None,
    model_responses_summary: Optional[str] = None
) -> ValidationError:
    """
    Save validation error to database.
    
    Args:
        candidate_id: ID of the candidate
        error_message: Error message describing the validation failure
        feedback_html_content: HTML content of the rejected feedback
        validation_results: JSON string of validation results
        model_responses_summary: Summary of model responses
        
    Returns:
        ValidationError object
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO validation_errors (candidate_id, error_message, feedback_html_content, validation_results, model_responses_summary)
        VALUES (?, ?, ?, ?, ?)
    ''', (candidate_id, error_message, feedback_html_content, validation_results, model_responses_summary))
    
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
        created_at=datetime.now()
    )


def get_validation_errors_for_candidate(candidate_id: int) -> List[ValidationError]:
    """Get all validation errors for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM validation_errors WHERE candidate_id = ? ORDER BY created_at DESC', (candidate_id,))
    rows = cursor.fetchall()
    conn.close()
    
    errors = []
    for row in rows:
        errors.append(ValidationError(
            id=row['id'],
            candidate_id=row['candidate_id'],
            error_message=row['error_message'],
            feedback_html_content=row['feedback_html_content'],
            validation_results=row['validation_results'],
            model_responses_summary=row['model_responses_summary'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        ))
    
    return errors


def get_all_validation_errors() -> List[ValidationError]:
    """Get all validation errors from database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM validation_errors ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    errors = []
    for row in rows:
        errors.append(ValidationError(
            id=row['id'],
            candidate_id=row['candidate_id'],
            error_message=row['error_message'],
            feedback_html_content=row['feedback_html_content'],
            validation_results=row['validation_results'],
            model_responses_summary=row['model_responses_summary'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        ))
    
    return errors


# ==================== TICKET FUNCTIONS ====================



"""Ticket CRUD functions to append to models.py"""
from datetime import datetime, timedelta
from typing import Optional, List
import sqlite3

# ==================== TICKET FUNCTIONS ====================

def create_ticket(
    department: TicketDepartment,
    priority: TicketPriority,
    description: str,
    deadline: Optional[datetime] = None,
    related_candidate_id: Optional[int] = None,
    related_email_id: Optional[str] = None,
    status: TicketStatus = TicketStatus.OPEN
) -> Ticket:
    """Create a new ticket."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tickets (department, priority, status, description, deadline, related_candidate_id, related_email_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        department.value if isinstance(department, TicketDepartment) else str(department),
        priority.value if isinstance(priority, TicketPriority) else str(priority),
        status.value if isinstance(status, TicketStatus) else str(status),
        description,
        deadline.isoformat() if deadline else None,
        related_candidate_id,
        related_email_id
    ))
    
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
        related_email_id=related_email_id
    )


def get_ticket_by_id(ticket_id: int) -> Optional[Ticket]:
    """Get ticket by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return Ticket(
        id=row['id'],
        department=TicketDepartment(row['department']),
        priority=TicketPriority(row['priority']),
        status=TicketStatus(row['status']),
        description=row['description'],
        deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
        related_candidate_id=row['related_candidate_id'],
        related_email_id=row['related_email_id'],
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
    )


def get_all_tickets() -> List[Ticket]:
    """Get all tickets."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tickets ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    tickets = []
    for row in rows:
        tickets.append(Ticket(
            id=row['id'],
            department=TicketDepartment(row['department']),
            priority=TicketPriority(row['priority']),
            status=TicketStatus(row['status']),
            description=row['description'],
            deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
            related_candidate_id=row['related_candidate_id'],
            related_email_id=row['related_email_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        ))
    
    return tickets


def update_ticket(
    ticket_id: int,
    department: Optional[TicketDepartment] = None,
    priority: Optional[TicketPriority] = None,
    status: Optional[TicketStatus] = None,
    description: Optional[str] = None,
    deadline: Optional[datetime] = None
) -> bool:
    """Update ticket."""
    conn = get_db()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if department is not None:
        updates.append('department = ?')
        values.append(department.value if isinstance(department, TicketDepartment) else str(department))
    
    if priority is not None:
        updates.append('priority = ?')
        values.append(priority.value if isinstance(priority, TicketPriority) else str(priority))
    
    if status is not None:
        updates.append('status = ?')
        values.append(status.value if isinstance(status, TicketStatus) else str(status))
    
    if description is not None:
        updates.append('description = ?')
        values.append(description)
    
    if deadline is not None:
        updates.append('deadline = ?')
        values.append(deadline.isoformat())
    
    if not updates:
        conn.close()
        return False
    
    updates.append('updated_at = CURRENT_TIMESTAMP')
    values.append(ticket_id)
    
    cursor.execute(f'UPDATE tickets SET {", ".join(updates)} WHERE id = ?', values)
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0


def delete_ticket(ticket_id: int) -> bool:
    """Delete ticket."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0


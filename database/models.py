"""Database models for candidates, positions, and feedback."""
import sqlite3
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
                 consent_for_other_positions: Optional[bool] = None,
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
        self.consent_for_other_positions = consent_for_other_positions
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
            'status': self.status.value,
            'stage': self.stage.value,
            'cv_path': self.cv_path,
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
                 sent_at: Optional[datetime] = None):
        self.id = id
        self.candidate_id = candidate_id
        self.email_content = email_content
        self.sent_at = sent_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'candidate_id': self.candidate_id,
            'email_content': self.email_content,
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
            'stage': self.stage.value if isinstance(self.stage, RecruitmentStage) else self.stage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }


def get_db_path() -> Path:
    """Get database file path."""
    db_dir = Path('data')
    db_dir.mkdir(exist_ok=True)
    return db_dir / 'recruitment.db'


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
    
    # Create feedback_emails table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            email_content TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    ''')
    
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
    
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at: {db_path}")


def get_all_candidates() -> List[Candidate]:
    """Get all candidates with their positions."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.*, p.title as position_title, p.company as position_company
        FROM candidates c
        LEFT JOIN positions p ON c.position_id = p.id
        ORDER BY c.created_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    candidates = []
    for row in rows:
        # Handle consent_for_other_positions (may not exist in older databases)
        consent_value = None
        if 'consent_for_other_positions' in row.keys() and row['consent_for_other_positions'] is not None:
            consent_value = bool(row['consent_for_other_positions'])
        
        candidate = Candidate(
            id=row['id'],
            first_name=row['first_name'],
            last_name=row['last_name'],
            email=row['email'],
            position_id=row['position_id'],
            status=CandidateStatus(row['status']),
            stage=RecruitmentStage(row['stage']),
            cv_path=row['cv_path'],
            consent_for_other_positions=consent_value,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
        # Add position info as attributes
        candidate.position_title = row['position_title'] if 'position_title' in row.keys() else ''
        candidate.position_company = row['position_company'] if 'position_company' in row.keys() else ''
        candidates.append(candidate)
    
    return candidates


def get_candidate_by_id(candidate_id: int) -> Optional[Candidate]:
    """Get candidate by ID."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.*, p.title as position_title, p.company as position_company, p.description as position_description
        FROM candidates c
        LEFT JOIN positions p ON c.position_id = p.id
        WHERE c.id = ?
    ''', (candidate_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    # Handle consent_for_other_positions (may not exist in older databases)
    consent_value = None
    if 'consent_for_other_positions' in row.keys() and row['consent_for_other_positions'] is not None:
        consent_value = bool(row['consent_for_other_positions'])
    
    candidate = Candidate(
        id=row['id'],
        first_name=row['first_name'],
        last_name=row['last_name'],
        email=row['email'],
        position_id=row['position_id'],
        status=CandidateStatus(row['status']),
        stage=RecruitmentStage(row['stage']),
        cv_path=row['cv_path'],
        consent_for_other_positions=consent_value,
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
    )
    candidate.position_title = row['position_title'] if 'position_title' in row.keys() else ''
    candidate.position_company = row['position_company'] if 'position_company' in row.keys() else ''
    candidate.position_description = row['position_description'] if 'position_description' in row.keys() else ''
    
    return candidate


def create_candidate(first_name: str, last_name: str, email: str, 
                     position_id: Optional[int] = None,
                     status: CandidateStatus = CandidateStatus.IN_PROGRESS,
                     stage: RecruitmentStage = RecruitmentStage.INITIAL_SCREENING,
                     cv_path: Optional[str] = None,
                     consent_for_other_positions: Optional[bool] = None) -> Candidate:
    """Create a new candidate."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Convert boolean to integer for SQLite (1 = True, 0 = False, NULL = None)
    consent_value = 1 if consent_for_other_positions is True else (0 if consent_for_other_positions is False else None)
    
    cursor.execute('''
        INSERT INTO candidates (first_name, last_name, email, position_id, status, stage, cv_path, consent_for_other_positions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (first_name, last_name, email, position_id, status.value, stage.value, cv_path, consent_value))
    
    candidate_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return get_candidate_by_id(candidate_id)


def update_candidate(candidate_id: int, **kwargs) -> Optional[Candidate]:
    """Update candidate fields."""
    conn = get_db()
    cursor = conn.cursor()
    
    allowed_fields = ['first_name', 'last_name', 'email', 'position_id', 'status', 'stage', 'cv_path', 'consent_for_other_positions']
    updates = []
    values = []
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            if key == 'status' and isinstance(value, CandidateStatus):
                value = value.value
            elif key == 'stage' and isinstance(value, RecruitmentStage):
                value = value.value
            elif key == 'consent_for_other_positions':
                # Convert boolean to integer for SQLite (1 = True, 0 = False, NULL = None)
                value = 1 if value is True else (0 if value is False else None)
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return get_candidate_by_id(candidate_id)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(candidate_id)
    
    cursor.execute(f'''
        UPDATE candidates
        SET {', '.join(updates)}
        WHERE id = ?
    ''', values)
    
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
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM positions WHERE id = ?', (position_id,))
    row = cursor.fetchone()
    conn.close()
    
    return Position(
        id=row['id'],
        title=row['title'],
        company=row['company'],
        description=row['description'],
        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
    )


def save_feedback_email(candidate_id: int, email_content: str) -> FeedbackEmail:
    """Save feedback email to database."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO feedback_emails (candidate_id, email_content)
        VALUES (?, ?)
    ''', (candidate_id, email_content))
    
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
            sent_at=datetime.fromisoformat(row['sent_at']) if row['sent_at'] else None
        ))
    
    return emails


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


def update_position(position_id: int, **kwargs) -> Optional[Position]:
    """Update position fields."""
    conn = get_db()
    cursor = conn.cursor()
    
    allowed_fields = ['title', 'company', 'description']
    updates = []
    values = []
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        conn.close()
        return get_position_by_id(position_id)
    
    values.append(position_id)
    
    cursor.execute(f'''
        UPDATE positions
        SET {', '.join(updates)}
        WHERE id = ?
    ''', values)
    
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


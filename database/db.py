"""Database connection and initialization."""

import sqlite3
from pathlib import Path

from core.logger import logger


def get_db_path() -> Path:
    """Get database file path."""
    db_dir = Path("data")
    db_dir.mkdir(exist_ok=True)
    return db_dir / "hr_database.db"


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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
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
    """
    )

    try:
        cursor.execute(
            "ALTER TABLE candidates ADD COLUMN consent_for_other_positions INTEGER DEFAULT NULL"
        )
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "UPDATE candidates SET consent_for_other_positions = 0 WHERE consent_for_other_positions IS NULL"
        )
    except sqlite3.OperationalError:
        pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            email_content TEXT NOT NULL,
            message_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """
    )

    try:
        cursor.execute("ALTER TABLE feedback_emails ADD COLUMN message_id TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hr_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER NOT NULL,
            notes TEXT NOT NULL,
            stage TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        )
    """
    )

    cursor.execute(
        """
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
    """
    )

    cursor.execute(
        """
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
    """
    )

    cursor.execute(
        """
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
    """
    )

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at: {db_path}")


def clear_database(reset_autoincrement: bool = True) -> None:
    """Clear all rows from application tables without dropping tables."""
    conn = get_db()
    cursor = conn.cursor()
    init_db()
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
        cursor.execute("PRAGMA foreign_keys = OFF;")
        for table in tables_in_delete_order:
            cursor.execute(f"DELETE FROM {table};")
        if reset_autoincrement:
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

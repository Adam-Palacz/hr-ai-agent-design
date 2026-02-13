"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile
import sys

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def use_test_database():
    """Use a temporary database file for the whole test session (before app is imported)."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="recruitment_test_"))
    test_db_path = tmp_dir / "data" / "hr_database.db"
    test_db_path.parent.mkdir(parents=True, exist_ok=True)

    import database.models as db_models

    original_get_db_path = db_models.get_db_path
    db_models.get_db_path = lambda: test_db_path
    db_models.init_db()

    yield

    db_models.get_db_path = original_get_db_path


@pytest.fixture(scope="session")
def app():
    """Flask application with TESTING enabled (import after DB patch)."""
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

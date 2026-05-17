"""Pytest configuration and shared fixtures."""

import os
import pytest
from pathlib import Path
import tempfile
import sys
from unittest.mock import MagicMock

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set dummy Azure OpenAI key so agents can be instantiated in tests (no real calls)
if not os.environ.get("AZURE_OPENAI_API_KEY"):
    os.environ["AZURE_OPENAI_API_KEY"] = "test-key-no-real-calls"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration (run with -m integration)"
    )
    config.addinivalue_line(
        "markers", "evaluation: marks tests that may use real LLM (run with RUN_LLM_EVAL=1)"
    )
    config.addinivalue_line(
        "markers",
        "ai_agent: marks tests for AI agent behaviour (mocked LLM unless evaluation)",
    )
    config.addinivalue_line(
        "markers",
        "live: real API/SMTP tests (run with LIVE_TEST=1, uses .env credentials)",
    )


@pytest.fixture(scope="session", autouse=True)
def use_test_database():
    """Use a temporary database file for the whole test session (before app is imported)."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="recruitment_test_"))
    test_db_path = tmp_dir / "data" / "hr_database.db"
    test_db_path.parent.mkdir(parents=True, exist_ok=True)

    import database.db as db_module

    original_get_db_path = db_module.get_db_path
    db_module.get_db_path = lambda: test_db_path
    db_module.init_db()

    yield

    db_module.get_db_path = original_get_db_path


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


# --- Fixtures for service/agent tests (mocks, sample data) ---


@pytest.fixture
def sample_cv_data():
    """Minimal CVData for feedback/cv tests."""
    from models.cv_models import CVData

    return CVData(
        full_name="Jan Testowy",
        email="jan@example.com",
        summary="Python developer, 5 years experience.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )


@pytest.fixture
def sample_hr_feedback():
    """Minimal HRFeedback for feedback tests."""
    from models.feedback_models import HRFeedback, Decision

    return HRFeedback(
        decision=Decision.REJECTED,
        notes="Strong technical skills but limited domain experience.",
        position_applied="Backend Developer",
        interviewer_name="HR Team",
    )


@pytest.fixture
def sample_job_offer():
    """Minimal JobOffer for feedback tests."""
    from models.job_models import JobOffer

    return JobOffer(
        title="Backend Developer",
        company="Test Corp",
        location="Warsaw",
        description="Python, REST APIs.",
    )


@pytest.fixture
def mock_openai_chat_completion():
    """Factory: returns a MagicMock that mimics Azure OpenAI chat.completions.create response."""

    def _make_mock(content: str):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        return mock_response

    return _make_mock


@pytest.fixture
def sample_feedback_html():
    """Valid HTML snippet for feedback/correction tests."""
    return (
        "<!DOCTYPE html><html><body>"
        "<p>Dear Jan,</p><p>Thank you for your application.</p>"
        "<p>Best regards,</p></body></html>"
    )

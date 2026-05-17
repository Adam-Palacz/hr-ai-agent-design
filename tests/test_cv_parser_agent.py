"""Unit tests for CV parser agent transform and skip-LLM mode."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.cv_parser_agent import CVParserAgent
from models.cv_models import CVData


@pytest.fixture
def parser():
    with patch.object(CVParserAgent, "__init__", lambda self, *a, **kw: None):
        agent = CVParserAgent.__new__(CVParserAgent)
        agent.model_name = "gpt-4o-mini"
        agent.temperature = 1.0
        agent.use_ocr = False
        agent.vision_model_name = None
        return agent


def test_transform_projects_as_dicts(parser):
    """LLM may return project objects instead of strings in additional_info."""
    data = {
        "full_name": "Jan Kowalski",
        "additional_info": {
            "projects": [
                {"name": "Cloud migration", "description": "AWS EKS rollout"},
                "Legacy refactor",
            ]
        },
    }
    transformed = parser._transform_llm_response(data)
    assert "Cloud migration" in transformed["additional_info"]
    assert "Legacy refactor" in transformed["additional_info"]
    assert "Projects:" in transformed["additional_info"]


def test_stringify_list_items_mixed_types(parser):
    items = [{"title": "Alpha", "role": "Lead"}, "Beta"]
    assert parser._stringify_list_items(items) == ["Alpha - Lead", "Beta"]


@patch("agents.cv_parser_agent.settings")
def test_parse_cv_from_pdf_skips_entirely_when_parsing_disabled(mock_settings, parser, tmp_path):
    mock_settings.cv_parsing_enabled = False
    mock_settings.cv_llm_parsing_enabled = True

    pdf_path = tmp_path / "jan-kowalski-cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    with (
        patch("agents.cv_parser_agent.extract_text_from_pdf") as mock_extract,
        patch.object(parser, "_chat") as mock_chat,
    ):
        result = parser.parse_cv_from_pdf(str(pdf_path), candidate_id=None)

    mock_extract.assert_not_called()
    mock_chat.assert_not_called()
    assert isinstance(result, CVData)
    assert result.summary is None
    assert "jan kowalski cv" in result.full_name.lower()


@patch("agents.cv_parser_agent.settings")
def test_parse_cv_from_pdf_skips_llm_when_disabled(mock_settings, parser, tmp_path):
    mock_settings.cv_parsing_enabled = True
    mock_settings.cv_llm_parsing_enabled = False
    mock_settings.max_text_length = 5000

    pdf_path = tmp_path / "jan-kowalski-cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    with (
        patch("agents.cv_parser_agent.extract_text_from_pdf", return_value="DevOps engineer CV text"),
        patch.object(parser, "_chat") as mock_chat,
    ):
        result = parser.parse_cv_from_pdf(str(pdf_path), candidate_id=None)

    mock_chat.assert_not_called()
    assert isinstance(result, CVData)
    assert "DevOps" in (result.summary or "")
    assert result.experience == []


@patch("agents.cv_parser_agent.settings")
def test_cv_data_from_extracted_text_uses_candidate(mock_settings, parser):
    mock_settings.max_text_length = 1000
    candidate = MagicMock()
    candidate.full_name = "Anna Z Test"
    candidate.email = "anna@test.pl"

    with patch("database.candidates.get_candidate_by_id", return_value=candidate):
        cv = parser._cv_data_from_extracted_text("raw cv", "/tmp/cv.pdf", candidate_id=42)

    assert cv.full_name == "Anna Z Test"
    assert cv.email == "anna@test.pl"
    assert cv.summary.startswith("raw cv")

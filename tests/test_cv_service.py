"""Unit tests for cv_service (mocked parser, no real PDF/LLM)."""

import pytest
from unittest.mock import MagicMock

from models.cv_models import CVData
from core.exceptions import PDFReadError, LLMError, ValidationError


@pytest.fixture
def mock_parser():
    """Parser that returns fixed CVData."""
    p = MagicMock()
    p.parse_cv_from_pdf.return_value = CVData(
        full_name="Anna Test",
        email="anna@example.com",
        summary="Developer with 5 years experience.",
        education=[],
        experience=[],
        skills=[],
        certifications=[],
        languages=[],
    )
    return p


def test_process_cv_from_pdf_success_returns_cv_data(mock_parser, tmp_path):
    """Happy path: existing PDF path returns CVData with expected fields."""
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 minimal\n")

    from services.cv_service import CVService

    service = CVService(parser_agent=mock_parser)
    result = service.process_cv_from_pdf(str(pdf_path))

    assert isinstance(result, CVData)
    assert result.full_name == "Anna Test"
    assert result.email == "anna@example.com"
    mock_parser.parse_cv_from_pdf.assert_called_once()
    call_kw = mock_parser.parse_cv_from_pdf.call_args[1]
    assert "verbose" in call_kw


def test_process_cv_from_pdf_file_not_found_raises():
    """When PDF path does not exist, raises PDFReadError."""
    from services.cv_service import CVService

    service = CVService(parser_agent=MagicMock())
    with pytest.raises(PDFReadError) as exc_info:
        service.process_cv_from_pdf("/nonexistent/file.pdf")

    assert "not found" in str(exc_info.value).lower() or "PDF" in str(exc_info.value)


def test_process_cv_from_pdf_not_pdf_raises(tmp_path):
    """When file is not .pdf, raises PDFReadError."""
    txt = tmp_path / "cv.txt"
    txt.write_text("not a pdf")

    from services.cv_service import CVService

    service = CVService(parser_agent=MagicMock())
    with pytest.raises(PDFReadError) as exc_info:
        service.process_cv_from_pdf(str(txt))

    assert "not a PDF" in str(exc_info.value) or "PDF" in str(exc_info.value)


def test_process_cv_from_pdf_parser_raises_llm_error(mock_parser, tmp_path):
    """When parser raises generic Exception, service raises LLMError."""
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    mock_parser.parse_cv_from_pdf.side_effect = Exception("API timeout")

    from services.cv_service import CVService

    service = CVService(parser_agent=mock_parser)
    with pytest.raises(LLMError):
        service.process_cv_from_pdf(str(pdf_path))


def test_process_cv_from_pdf_parser_raises_pdf_error(mock_parser, tmp_path):
    """When parser raises Exception with 'PDF' in message, service raises PDFReadError."""
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    mock_parser.parse_cv_from_pdf.side_effect = Exception("Failed to read PDF structure")

    from services.cv_service import CVService

    service = CVService(parser_agent=mock_parser)
    with pytest.raises(PDFReadError):
        service.process_cv_from_pdf(str(pdf_path))


def test_process_cv_from_pdf_parser_raises_validation_error(mock_parser, tmp_path):
    """When parser raises Exception with 'validation' in message, service raises ValidationError."""
    pdf_path = tmp_path / "cv.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    mock_parser.parse_cv_from_pdf.side_effect = Exception("pydantic validation error")

    from services.cv_service import CVService

    service = CVService(parser_agent=mock_parser)
    with pytest.raises(ValidationError):
        service.process_cv_from_pdf(str(pdf_path))

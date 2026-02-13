"""CV processing service layer."""

from pathlib import Path
from typing import Optional

from core.logger import logger
from core.exceptions import PDFReadError, ValidationError, LLMError
from agents.cv_parser_agent import CVParserAgent
from models.cv_models import CVData


class CVService:
    """Service for processing CV documents."""

    def __init__(self, parser_agent: CVParserAgent):
        """
        Initialize CV service.

        Args:
            parser_agent: Initialized CVParserAgent instance
        """
        self.parser = parser_agent
        logger.info("CVService initialized")

    def process_cv_from_pdf(
        self, pdf_path: str, verbose: bool = False, candidate_id: Optional[int] = None
    ) -> CVData:
        """
        Process CV from PDF file with proper error handling.

        Args:
            pdf_path: Path to PDF file
            verbose: Enable verbose logging

        Returns:
            Parsed CVData object

        Raises:
            PDFReadError: If PDF cannot be read
            ValidationError: If CV data is invalid
            LLMError: If LLM processing fails
        """
        pdf_path_obj = Path(pdf_path)

        # Validate file exists
        if not pdf_path_obj.exists():
            error_msg = f"PDF file not found: {pdf_path}"
            logger.error(error_msg)
            raise PDFReadError(error_msg)

        if not pdf_path_obj.suffix.lower() == ".pdf":
            error_msg = f"File is not a PDF: {pdf_path}"
            logger.error(error_msg)
            raise PDFReadError(error_msg)

        logger.info(f"Processing CV from PDF: {pdf_path}")
        logger.info(f"File size: {pdf_path_obj.stat().st_size / 1024:.2f} KB")
        logger.info(f"Verbose mode: {verbose}")

        try:
            logger.info("Starting CV parsing process...")
            cv_data = self.parser.parse_cv_from_pdf(
                str(pdf_path_obj), verbose=verbose, candidate_id=candidate_id
            )
            logger.info(f"Successfully parsed CV for: {cv_data.full_name}")
            logger.info(
                f"Extracted data: {len(cv_data.education)} education entries, {len(cv_data.experience)} experience entries, {len(cv_data.skills)} skills"
            )
            return cv_data

        except Exception as e:
            error_msg = f"Failed to process CV: {str(e)}"
            logger.error(error_msg, exc_info=True)

            if "PDF" in str(e) or "pdf" in str(e):
                raise PDFReadError(error_msg) from e
            elif "validation" in str(e).lower() or "pydantic" in str(e).lower():
                raise ValidationError(error_msg) from e
            else:
                raise LLMError(error_msg) from e

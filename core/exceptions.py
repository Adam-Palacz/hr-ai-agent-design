"""Custom exceptions for the application."""


class CVProcessingError(Exception):
    """Base exception for CV processing errors."""
    pass


class PDFReadError(CVProcessingError):
    """Error reading or parsing PDF file."""
    pass


class OCRError(CVProcessingError):
    """Error during OCR processing."""
    pass


class LLMError(CVProcessingError):
    """Error during LLM API call."""
    pass


class ValidationError(CVProcessingError):
    """Error validating CV data structure."""
    pass


class ConfigurationError(CVProcessingError):
    """Error in application configuration."""
    pass


"""Application constants."""


class ModelNames:
    """Default model names."""

    DEFAULT_PARSING = "gpt-3.5-turbo"
    DEFAULT_VISION = "gpt-4o"
    DEFAULT_FEEDBACK = "gpt-3.5-turbo"


class Timeouts:
    """Timeout values in seconds."""

    LLM_REQUEST = 120
    OCR_REQUEST = 180
    PDF_PROCESSING = 300


class Limits:
    """Size and length limits."""

    MAX_TEXT_LENGTH = 15000
    PDF_MIN_TEXT_THRESHOLD = 100
    MAX_PDF_PAGES = 50


class Messages:
    """Common user-facing messages."""

    PDF_NOT_FOUND = "PDF file not found: {path}"
    API_KEY_MISSING = "OPENAI_API_KEY not found. Set it in .env file or environment variable."
    PROCESSING_START = "Processing CV from PDF: {path}"
    PROCESSING_SUCCESS = "Successfully processed CV for: {name}"
    PROCESSING_ERROR = "Error processing CV: {error}"

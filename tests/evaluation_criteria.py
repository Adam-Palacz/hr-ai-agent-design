"""
Shared automated criteria for LLM-generated recruitment feedback (HTML).

Used by unit tests (mock LLM) and optional real-API evaluation (RUN_LLM_EVAL=1).
"""

from __future__ import annotations

import re
from typing import List, Optional

from models.validation_models import _is_likely_html, _is_parseable_html

# --- Reference fixtures for evaluation runs ---

REFERENCE_CV_SUMMARY = "5+ years Python, REST APIs, SQL. MSc Computer Science."
REFERENCE_POSITION = "Backend Developer"
REFERENCE_COMPANY = "Test Corp"
REFERENCE_CANDIDATE_NAME = "Jan Kowalski"
REFERENCE_CANDIDATE_EMAIL = "jan.kowalski@example.com"

DISALLOWED_PLACEHOLDER_WORDS = ["TODO", "Lorem", "INSERT", "FIXME", "XXX", "[Stanowisko]", "[Firma]"]

DISCRIMINATORY_TERMS = [
    "too old",
    "too young",
    "za stary",
    "za młoda",
    "ciąż",
    "religij",
    "rasow",
    "płci",
    "niepełnospraw",
]

REJECTION_TONE_MARKERS = [
    "z przykrością",
    "niestety",
    "nie możemy",
    "odmawiamy",
    "innych kandydat",
    "nie została wybrana",
    "nie został wybrany",
    "decyzja negatywna",
]

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(\+48\s?)?(\d{3}[\s-]?\d{3}[\s-]?\d{3}|\d{9})")


def llm_eval_api_configured() -> bool:
    """True when credentials exist for the configured LLM_PROVIDER."""
    from config import settings

    if settings.uses_openai_provider:
        return bool(settings.openai_api_key)
    return settings.is_azure_configured


def check_html_valid(html: str) -> bool:
    if not html or not isinstance(html, str):
        return False
    return _is_likely_html(html) and _is_parseable_html(html)


def check_length_reasonable(html: str, min_len: int = 200, max_len: int = 8000) -> bool:
    return min_len <= len(html) <= max_len


def check_no_disallowed_words(html: str, words: Optional[List[str]] = None) -> bool:
    words = words or DISALLOWED_PLACEHOLDER_WORDS
    html_lower = html.lower()
    return not any(w.lower() in html_lower for w in words)


def check_no_email_leak(html: str, known_emails: Optional[List[str]] = None) -> bool:
    known_emails = known_emails or []
    for email in known_emails:
        if email and email.lower() in html.lower():
            return False
    return EMAIL_PATTERN.search(html) is None


def check_no_phone_leak(html: str) -> bool:
    return PHONE_PATTERN.search(html) is None


def check_rejection_tone(html: str) -> bool:
    html_lower = html.lower()
    return any(marker in html_lower for marker in REJECTION_TONE_MARKERS)


def check_mentions_position(html: str, position: str) -> bool:
    if not position:
        return True
    return position.lower() in html.lower()


def check_no_discriminatory_language(html: str) -> bool:
    html_lower = html.lower()
    return not any(term in html_lower for term in DISCRIMINATORY_TERMS)


def evaluate_feedback_html(
    html: str,
    *,
    position: Optional[str] = None,
    candidate_emails: Optional[List[str]] = None,
) -> List[str]:
    """
    Run all feedback quality checks. Returns a list of human-readable failure messages (empty = pass).
    """
    failures: List[str] = []
    if not check_html_valid(html):
        failures.append("HTML is missing, not parseable, or not valid markup")
    if not check_length_reasonable(html):
        failures.append(f"HTML length {len(html)} outside reasonable range")
    if not check_no_disallowed_words(html):
        failures.append("Contains placeholder or disallowed words")
    if not check_no_email_leak(html, candidate_emails):
        failures.append("Contains candidate email or other raw email address")
    if not check_no_phone_leak(html):
        failures.append("Contains phone number pattern (possible PII leak)")
    if not check_rejection_tone(html):
        failures.append("Missing clear rejection tone (expected Polish HR phrasing)")
    if position and not check_mentions_position(html, position):
        failures.append(f"Does not mention position: {position}")
    if not check_no_discriminatory_language(html):
        failures.append("Contains potentially discriminatory language")
    return failures

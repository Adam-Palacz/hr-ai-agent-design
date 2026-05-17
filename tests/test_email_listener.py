"""Tests for email listener classification helpers."""

from types import SimpleNamespace

from services.email_listener import EmailListener


def test_iod_fast_path_does_not_match_dpo_inside_odpowiedz():
    listener = EmailListener("bot@example.com", "password")

    result = listener._classify_iod_by_keywords(
        {
            "subject": "Re: Odpowiedź na aplikację - Senior DevOps Engineer",
            "body": "Nie chce brac udzialu w dalszych rekrutacjach",
        }
    )

    assert result == "default"


def test_iod_fast_path_matches_dpo_as_separate_token():
    listener = EmailListener("bot@example.com", "password")

    result = listener._classify_iod_by_keywords(
        {
            "subject": "Pytanie do DPO",
            "body": "Proszę o informację dotyczącą danych osobowych.",
        }
    )

    assert result == "iod"


def test_classify_email_uses_llm_for_consent_no_after_iod_fast_path_default():
    listener = EmailListener("bot@example.com", "password")

    classifier = SimpleNamespace(
        classify_email=lambda **kwargs: SimpleNamespace(category="consent_no", confidence=0.94)
    )

    result = listener.classify_email(
        {
            "from_email": "adam.palacz96@gmail.com",
            "subject": "Re: Odpowiedź na aplikację - Senior DevOps Engineer",
            "body": "Nie chce brac udzialu w dalszych rekrutacjach",
        },
        classifier_agent=classifier,
    )

    assert result == "consent_no"


def test_classify_email_fallback_negative_consent_wins_over_other_recruitments_context():
    listener = EmailListener("bot@example.com", "password")

    result = listener.classify_email(
        {
            "subject": "Re: Odpowiedź na aplikację - Senior DevOps Engineer",
            "body": "Nie chce brac udzialu w dalszych rekrutacjach",
        },
        classifier_agent=None,
    )

    assert result == "consent_no"


def test_classify_email_fallback_positive_consent():
    listener = EmailListener("bot@example.com", "password")

    result = listener.classify_email(
        {
            "subject": "Zgoda",
            "body": "Wyrażam zgodę na udział w innych rekrutacjach",
        },
        classifier_agent=None,
    )

    assert result == "consent_yes"

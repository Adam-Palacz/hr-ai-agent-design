"""Tests for EmailClassifierAgent (mocked LLM + IOD keyword gate logic)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.email_classifier_agent import EmailClassifierAgent, EmailClassification


def _classification_json(category: str, confidence: float = 0.92) -> str:
    return json.dumps(
        {
            "category": category,
            "confidence": confidence,
            "reasoning": "test",
            "keywords_found": [],
        }
    )


@patch("agents.base_agent.get_llm_client")
def test_classify_email_consent_yes(mock_get_llm):
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_classification_json("consent_yes"), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = EmailClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_email(
        "kandydat@test.com",
        "Zgoda",
        "Wyrażam zgodę na udział w innych rekrutacjach.",
    )

    assert result.category == "consent_yes"
    assert result.confidence >= 0.5


@patch("agents.base_agent.get_llm_client")
def test_classify_email_consent_no(mock_get_llm):
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_classification_json("consent_no"), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = EmailClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_email(
        "kandydat@test.com",
        "Re: Odpowiedź na aplikację",
        "Nie chce brac udzialu w dalszych rekrutacjach.",
    )

    assert result.category == "consent_no"
    assert result.confidence >= 0.5


@patch("agents.base_agent.get_llm_client")
def test_classify_email_iod_kept_with_keywords(mock_get_llm):
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_classification_json("iod", 0.9), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = EmailClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_email(
        "kandydat@test.com",
        "RODO",
        "Proszę o informację o przetwarzaniu moich danych osobowych.",
    )

    assert result.category == "iod"


@patch("agents.base_agent.get_llm_client")
def test_classify_email_iod_downgraded_without_keywords_low_confidence(mock_get_llm):
    """False IOD: model says iod but no keyword/hint and low confidence → default."""
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_classification_json("iod", 0.4), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = EmailClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_email(
        "kandydat@test.com",
        "Pytanie",
        "Kiedy mogę spodziewać się odpowiedzi na moją aplikację?",
    )

    assert result.category == "default"


@patch("agents.base_agent.get_llm_client")
def test_classify_email_iod_semantic_high_confidence_without_keywords(mock_get_llm):
    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (
        _classification_json("iod", EmailClassifierAgent.IOD_SEMANTIC_MIN_CONFIDENCE),
        MagicMock(),
    )
    mock_get_llm.return_value = mock_adapter

    agent = EmailClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_email(
        "kandydat@test.com",
        "Erasure request",
        "Please erase my applicant profile from your recruitment database.",
        apply_iod_keyword_gate=True,
    )

    assert result.category == "iod"


@patch("agents.base_agent.get_llm_client")
def test_classify_email_llm_failure_returns_default(mock_get_llm):
    mock_adapter = MagicMock()
    mock_adapter.complete.side_effect = RuntimeError("API down")
    mock_get_llm.return_value = mock_adapter

    agent = EmailClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_email("x@test.com", "S", "Body")

    assert isinstance(result, EmailClassification)
    assert result.category == "default"
    assert result.confidence == 0.5

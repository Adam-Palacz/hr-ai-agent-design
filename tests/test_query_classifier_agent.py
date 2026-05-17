"""Tests for QueryClassifierAgent routing decisions (mocked LLM)."""

import json
from unittest.mock import MagicMock, patch

import pytest


def _query_result(action: str, confidence: float = 0.85) -> str:
    return json.dumps(
        {
            "action": action,
            "confidence": confidence,
            "reasoning": "test",
            "suggested_response": "",
        }
    )


@patch("agents.base_agent.get_llm_client")
def test_classify_query_direct_answer_high_confidence(mock_get_llm):
    from agents.query_classifier_agent import QueryClassifierAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_query_result("direct_answer", 0.9), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = QueryClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_query("Pytanie", "Ile trwa proces rekrutacji?", "a@b.com")

    assert result["action"] == "direct_answer"
    assert result["confidence"] == 0.9


@patch("agents.base_agent.get_llm_client")
def test_classify_query_rag_low_confidence_forwards_to_hr(mock_get_llm):
    from agents.query_classifier_agent import QueryClassifierAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_query_result("rag_answer", 0.4), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = QueryClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_query("RODO", "Jak długo przechowujecie CV?", "a@b.com")

    assert result["action"] == "forward_to_hr"
    assert "0.5" in result["reasoning"] or "too low" in result["reasoning"].lower()


@patch("agents.base_agent.get_llm_client")
def test_classify_query_direct_answer_low_confidence_forwards_to_hr(mock_get_llm):
    from agents.query_classifier_agent import QueryClassifierAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (_query_result("direct_answer", 0.5), MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = QueryClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_query("Pytanie", "Czy mogę zmienić termin?", "a@b.com")

    assert result["action"] == "forward_to_hr"


@patch("agents.base_agent.get_llm_client")
def test_classify_query_invalid_action_defaults_to_hr(mock_get_llm):
    from agents.query_classifier_agent import QueryClassifierAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (
        json.dumps({"action": "magic", "confidence": 0.99, "reasoning": "x"}),
        MagicMock(),
    )
    mock_get_llm.return_value = mock_adapter

    agent = QueryClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_query("S", "B", "a@b.com")

    assert result["action"] == "forward_to_hr"


@patch("agents.base_agent.get_llm_client")
def test_classify_query_api_error_forwards_to_hr(mock_get_llm):
    from agents.query_classifier_agent import QueryClassifierAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.side_effect = ValueError("bad json")
    mock_get_llm.return_value = mock_adapter

    agent = QueryClassifierAgent(model_name="gpt-4o-mini")
    result = agent.classify_query("S", "B", "a@b.com")

    assert result["action"] == "forward_to_hr"
    assert result["confidence"] == 0.0

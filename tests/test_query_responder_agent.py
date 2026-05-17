"""Tests for QueryResponderAgent response generation (mocked LLM)."""

from unittest.mock import MagicMock, patch


@patch("agents.base_agent.get_llm_client")
def test_generate_response_direct_answer_adds_privacy_link(mock_get_llm):
    from agents.query_responder_agent import QueryResponderAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (
        "Proces rekrutacji trwa zwykle kilka etapów.\n\nZ wyrazami szacunku\n\nDział HR",
        MagicMock(),
    )
    mock_get_llm.return_value = mock_adapter

    agent = QueryResponderAgent(model_name="gpt-4o-mini")
    result = agent.generate_response("Etapy", "Ile etapów ma rekrutacja?", "a@b.com")

    assert result is not None
    assert "Proces rekrutacji" in result
    assert "Informacje o przetwarzaniu danych osobowych" in result


@patch("agents.base_agent.get_llm_client")
def test_generate_response_forward_to_hr_signal_returns_none(mock_get_llm):
    from agents.query_responder_agent import QueryResponderAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = ("FORWARD_TO_HR", MagicMock())
    mock_get_llm.return_value = mock_adapter

    agent = QueryResponderAgent(model_name="gpt-4o-mini")
    result = agent.generate_response("Status", "Jaki jest status mojej aplikacji?", "a@b.com")

    assert result is None


@patch("agents.base_agent.get_llm_client")
def test_generate_response_uncertainty_phrase_returns_none(mock_get_llm):
    from agents.query_responder_agent import QueryResponderAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (
        "Nie posiadamy szczegółowych informacji w tej sprawie.\n\nZ wyrazami szacunku\n\nDział HR",
        MagicMock(),
    )
    mock_get_llm.return_value = mock_adapter

    agent = QueryResponderAgent(model_name="gpt-4o-mini")
    result = agent.generate_response("Pytanie", "Szczegóły?", "a@b.com")

    assert result is None


@patch("agents.base_agent.get_llm_client")
def test_generate_response_with_rag_context_includes_context_in_prompt(mock_get_llm):
    from agents.query_responder_agent import QueryResponderAgent

    mock_adapter = MagicMock()
    mock_adapter.complete.return_value = (
        "CV przechowujemy przez 6 miesięcy.\n\nZ wyrazami szacunku\n\nDział HR",
        MagicMock(),
    )
    mock_get_llm.return_value = mock_adapter

    agent = QueryResponderAgent(model_name="gpt-4o-mini")
    result = agent.generate_response(
        "RODO",
        "Jak długo przechowujecie CV?",
        "a@b.com",
        rag_context=[
            {
                "document": "CV kandydatów przechowujemy przez 6 miesięcy.",
                "metadata": {"source": "polityka_rekrutacji.txt"},
            }
        ],
    )

    assert result is not None
    user_prompt = mock_adapter.complete.call_args.kwargs["messages"][1]["content"]
    assert "ADDITIONAL CONTEXT FROM KNOWLEDGE BASE" in user_prompt
    assert "polityka_rekrutacji.txt" in user_prompt
    assert "CV kandydatów przechowujemy przez 6 miesięcy." in user_prompt

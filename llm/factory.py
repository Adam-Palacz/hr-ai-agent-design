from __future__ import annotations

from typing import Optional

from config import settings
from core.logger import logger
from llm.base import LLMAdapter
from llm.azure_openai import AzureLLMAdapter
from llm.openai_official import OpenAILLMAdapter

_adapter: Optional[LLMAdapter] = None


def get_llm_client() -> LLMAdapter:
    """
    Return a singleton LLMAdapter instance based on configuration.

    Default provider is Azure (current behaviour).
    """
    global _adapter
    if _adapter is not None:
        return _adapter

    provider = getattr(settings, "llm_provider", "azure").lower()

    if provider in ("", "azure"):
        _adapter = AzureLLMAdapter()
        logger.info(
            "LLM client initialized: provider=azure, adapter=%s, endpoint=%s, deployment=%s",
            type(_adapter).__name__,
            getattr(settings, "azure_openai_endpoint", "unknown"),
            getattr(settings, "azure_openai_gpt_deployment", "unknown"),
        )
    elif provider == "openai":
        _adapter = OpenAILLMAdapter()
        logger.info(
            "LLM client initialized: provider=openai, adapter=%s, base_url=%s, model=%s",
            type(_adapter).__name__,
            getattr(settings, "openai_base_url", "https://api.openai.com/v1"),
            getattr(settings, "openai_chat_model", "gpt-4o-mini"),
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER '{provider}'")

    return _adapter

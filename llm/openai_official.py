from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from config import settings
from llm.base import LLMAdapter


class OpenAILLMAdapter(LLMAdapter):
    """LLM adapter backed by the official OpenAI API (api.openai.com)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        api_key_to_use = api_key or settings.openai_api_key  # type: ignore[attr-defined]
        base_url_to_use = base_url or settings.openai_base_url  # type: ignore[attr-defined]
        self.default_model = default_model or settings.openai_chat_model  # type: ignore[attr-defined]

        if base_url_to_use:
            self.client = OpenAI(api_key=api_key_to_use, base_url=base_url_to_use)
        else:
            self.client = OpenAI(api_key=api_key_to_use)

    def complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Any]:
        model_name = model or self.default_model or "gpt-4o-mini"

        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            **kwargs,
        )

        content = response.choices[0].message.content or ""
        return content, response

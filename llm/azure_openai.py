from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from openai import AzureOpenAI

from config import settings
from llm.base import LLMAdapter


class AzureLLMAdapter(LLMAdapter):
    """LLM adapter backed by Azure OpenAI chat completions."""

    def __init__(self, api_key: Optional[str] = None):
        api_key_to_use = api_key or settings.api_key
        self.client = AzureOpenAI(
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=api_key_to_use,
        )

    def complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Any]:
        model_name = model or settings.openai_model

        response = self.client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            **kwargs,
        )

        content = response.choices[0].message.content or ""
        return content, response

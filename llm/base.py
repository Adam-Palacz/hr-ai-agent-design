from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Tuple

"""
LLM adapter interfaces.

These abstractions let the application talk to "an LLM" via a single
contract, while concrete implementations can use Azure OpenAI, OpenAI
official, or other providers.
"""


class LLMAdapter(Protocol):
    """Protocol for chat-completion style LLMs."""

    def complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[str, Any]:
        """
        Run a chat completion and return the generated content and raw response.

        Args:
            messages: List of role/content dicts in OpenAI format.
            model: Optional model/deployment name.
            temperature: Sampling temperature.
            max_completion_tokens: Optional max tokens for the completion.
            **kwargs: Provider-specific extra parameters.

        Returns:
            Tuple of (content, raw_response) where `content` is the assistant
            message text and `raw_response` is the provider response object.
        """

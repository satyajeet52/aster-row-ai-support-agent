"""
Mistral AI provider using the official mistralai Python package.
Uses the free tier (mistral-small-latest) by default.
Supports tool/function calling for order lookups.
"""

import json
import logging
from typing import Any

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from app.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class MistralProvider(LLMProvider):
    """
    Connects to the Mistral API. Reads the API key and model name
    from the Config object passed at initialization.
    """

    def __init__(self, api_key: str, model: str = "mistral-small-latest"):
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required for the Mistral provider")
        self._client = Mistral(api_key=api_key)
        self._model = model

    def name(self) -> str:
        return f"Mistral ({self._model})"

    # Sends messages to Mistral, optionally with tool definitions,
    # and parses the response into a provider-agnostic LLMResponse.
    def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = self._client.chat.complete(**kwargs)
            choice = response.choices[0].message

            tool_calls = []
            if choice.tool_calls:
                for tc in choice.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                        if isinstance(tc.function.arguments, str)
                        else tc.function.arguments,
                    })

            return LLMResponse(
                content=choice.content or "",
                tool_calls=tool_calls,
                raw=response,
            )
        except Exception as e:
            logger.error("Mistral API error: %s", e)
            raise

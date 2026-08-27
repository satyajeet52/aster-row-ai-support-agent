"""
Ollama provider that communicates with a local Ollama instance via HTTP.
Provided for users who have Ollama installed; not the default.
"""

import json
import logging
from typing import Any

import httpx

from app.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Talks to a running Ollama server over its HTTP API.
    Supports tool calling if the selected Ollama model supports it.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def name(self) -> str:
        return f"Ollama ({self._model})"

    # Sends a chat completion request to Ollama's /api/chat endpoint
    # and converts the response into a provider-agnostic LLMResponse.
    def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()

            message = data.get("message", {})
            content = message.get("content", "")

            tool_calls = []
            for tc in message.get("tool_calls", []):
                func = tc.get("function", {})
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": func.get("name", ""),
                    "arguments": func.get("arguments", {}),
                })

            return LLMResponse(content=content, tool_calls=tool_calls, raw=data)
        except Exception as e:
            logger.error("Ollama API error: %s", e)
            raise

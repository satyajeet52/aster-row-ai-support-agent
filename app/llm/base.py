"""
Abstract base class for LLM providers.
All providers (Mistral, Ollama, etc.) implement this interface so the
agent can swap providers without code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Structured response from any LLM provider."""
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None


class LLMProvider(ABC):
    """
    Interface that every LLM backend must implement.
    Accepts a list of chat messages and optional tool definitions,
    returns a structured LLMResponse.
    """

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send messages to the LLM and return a structured response."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return a human-readable name for this provider."""
        ...

"""Base provider interface for LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    duration_seconds: float = 0.0
    model_name: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract interface for reasoning providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        schema: dict[str, Any] | None = None,
        timeout_seconds: int = 120,
    ) -> LLMResponse:
        """Generate a response given a prompt and optional system prompt."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available to execute."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier."""
        ...

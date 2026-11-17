"""Provider factory for instantiating LLM backends."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.providers.agy_cli import AgyCliProvider
from backend.providers.base import BaseProvider
from backend.providers.google_api import GoogleGenAIProvider
from backend.providers.mock_provider import MockProvider

if TYPE_CHECKING:
    from backend.config import Settings

logger = logging.getLogger(__name__)


def get_provider(
    spec: str | None = None,
    settings: Settings | None = None,
) -> BaseProvider:
    """Resolve a model specification to an active BaseProvider instance.

    Supported specs:
      - agy/gemini-3.8-flash-medium (default, zero cost)
      - agy/gemini-3.8-flash-high
      - agy/gemini-3.8-flash-low
      - google/gemini-2.5-flash (requires GEMINI_API_KEY)
      - mock/default (offline test provider)
    """
    model_spec = spec or (settings.default_model if settings else "agy/gemini-3.8-flash-medium")

    parts = model_spec.split("/", 1)
    provider_type = parts[0].lower()
    model_name = parts[1] if len(parts) > 1 else "gemini-3.8-flash-medium"

    if provider_type == "mock":
        return MockProvider(model_name=model_name)

    if provider_type == "agy":
        agy_path = getattr(settings, "agy_cli_path", None) if settings else None
        effort = getattr(settings, "reasoning_effort", "medium") if settings else "medium"
        provider = AgyCliProvider(
            model=model_name,
            executable_path=agy_path,
            effort=effort,
        )
        if not provider.is_available():
            logger.warning(f"Agy CLI executable not found at specified paths.")
        return provider

    if provider_type == "google":
        api_key = getattr(settings, "gemini_api_key", "") if settings else ""
        return GoogleGenAIProvider(api_key=api_key, model=model_name)

    raise ValueError(
        f"Unsupported model provider spec: '{model_spec}'. "
        f"Available providers: agy/gemini-3.8-flash-medium, google/gemini-2.5-flash, mock/default."
    )

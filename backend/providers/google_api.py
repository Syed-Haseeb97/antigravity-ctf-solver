"""Google GenAI SDK provider adapter (optional, used when GEMINI_API_KEY is provided)."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from backend.providers.base import BaseProvider, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)


class GoogleGenAIProvider(BaseProvider):
    """Adapter for Google Gemini API via the official google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self._client: Any = None

    @property
    def name(self) -> str:
        return f"google/{self.model}"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("google-genai package is not installed.")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        schema: dict[str, Any] | None = None,
        timeout_seconds: int = 120,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        client = self._get_client()

        # Run synchronous SDK call in thread pool
        def _call() -> Any:
            config = {}
            if system_prompt:
                config["system_instruction"] = system_prompt
            return client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config if config else None,
            )

        start_time = asyncio.get_event_loop().time()
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(_call),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Google GenAI API call timed out after {timeout_seconds}s")
        except Exception as e:
            raise RuntimeError(f"Google GenAI API call failed: {e}") from e

        duration = asyncio.get_event_loop().time() - start_time
        response_text = resp.text or ""

        # Extract usage if present
        usage = LLMUsage()
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            meta = resp.usage_metadata
            usage.input_tokens = getattr(meta, "prompt_token_count", 0) or 0
            usage.output_tokens = getattr(meta, "candidates_token_count", 0) or 0
            usage.total_tokens = getattr(meta, "total_token_count", 0) or 0

        return LLMResponse(
            text=response_text.strip(),
            usage=usage,
            duration_seconds=duration,
            model_name=self.model,
            raw={"response": str(resp)},
        )

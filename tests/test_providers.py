"""Unit tests for reasoning model provider adapters."""

import pytest
from backend.providers.base import LLMResponse, LLMUsage
from backend.providers.factory import get_provider
from backend.providers.mock_provider import MockProvider
from backend.providers.agy_cli import AgyCliProvider


@pytest.mark.asyncio
async def test_mock_provider_generate():
    provider = MockProvider(
        responses=['{"thought": "test", "hypothesis": "b64", "action": "submit_flag", "command": "flag{test}"}']
    )
    assert provider.is_available() is True
    assert provider.name == "mock/mock-gemini-3.8-flash"

    resp = await provider.generate("Solve challenge")
    assert isinstance(resp, LLMResponse)
    assert "flag{test}" in resp.text
    assert resp.usage.total_tokens > 0
    assert len(provider.call_history) == 1


@pytest.mark.asyncio
async def test_mock_provider_fallback_when_empty():
    provider = MockProvider()
    resp = await provider.generate("No responses configured")
    assert "give_up" in resp.text


def test_factory_routing():
    mock_p = get_provider("mock/test-model")
    assert isinstance(mock_p, MockProvider)
    assert mock_p.model == "test-model"

    agy_p = get_provider("agy/gemini-3.8-flash-medium")
    assert isinstance(agy_p, AgyCliProvider)
    assert agy_p.model == "gemini-3.8-flash-medium"

    with pytest.raises(ValueError, match="Unsupported model provider"):
        get_provider("invalid/provider")


def test_agy_cli_resolver():
    provider = AgyCliProvider()
    assert provider.name == "agy/gemini-3.8-flash-low"

import json
from typing import Any

import httpx
import pytest
import respx

from app.core.config import settings
from app.services.llm.base import (
    LLMProvider,
    execute_with_retry,
    parse_json_from_llm_response,
)
from app.services.llm.budget import TokenBudgetHelper
from app.services.llm.exceptions import (
    InvalidAPIKeyError,
    ModelResponseError,
    ProviderUnavailableError,
    RateLimitError,
)
from app.services.llm.factory import get_llm_provider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.groq import GroqProvider

# ---------------------------------------------------------------------------
# TokenBudgetHelper Tests
# ---------------------------------------------------------------------------


def test_token_budget_estimation() -> None:
    assert TokenBudgetHelper.estimate_tokens("") == 0
    assert TokenBudgetHelper.estimate_tokens("word") == 1
    long_text = "a" * 400
    assert TokenBudgetHelper.estimate_tokens(long_text) == 100
    assert TokenBudgetHelper.fits_budget(long_text, 100) is True
    assert TokenBudgetHelper.fits_budget(long_text, 50) is False


def test_token_budget_truncation() -> None:
    text = "Machine learning algorithms require substantial training data and compute."
    truncated = TokenBudgetHelper.truncate_to_budget(text, max_tokens=6)
    assert len(truncated) < len(text)
    assert TokenBudgetHelper.fits_budget(truncated, 6) is True


def test_token_budget_chunking() -> None:
    text = (
        "Paragraph 1 contains some basic intro text.\n\n"
        "Paragraph 2 discusses distributed database consistency.\n\n"
        "Paragraph 3 covers neural network optimization techniques."
    )
    # Each paragraph has ~10-12 tokens
    chunks = TokenBudgetHelper.chunk_text(text, max_tokens=15, overlap_tokens=5)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert TokenBudgetHelper.fits_budget(chunk, 15) is True


# ---------------------------------------------------------------------------
# JSON Response Parser Tests
# ---------------------------------------------------------------------------


def test_parse_json_from_raw_and_markdown() -> None:
    raw = '{"name": "Python", "confidence": 0.95}'
    assert parse_json_from_llm_response(raw) == {"name": "Python", "confidence": 0.95}

    markdown = '```json\n{"category": "DevOps", "skills": ["Docker", "K8s"]}\n```'
    parsed = parse_json_from_llm_response(markdown)
    assert isinstance(parsed, dict)
    assert parsed["category"] == "DevOps"
    assert "Docker" in parsed["skills"]

    with pytest.raises(ModelResponseError, match="Failed to decode JSON"):
        parse_json_from_llm_response("Not valid json at all")

    with pytest.raises(ModelResponseError, match="Expected JSON object or array"):
        parse_json_from_llm_response('"just a string"')


# ---------------------------------------------------------------------------
# GeminiProvider Mocked Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_gemini_extract_json_success() -> None:
    expected_data = {"skills": [{"name": "PostgreSQL", "confidence": 0.9}]}
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent"
    )
    mock_route = respx.post(url).mock(
        return_value=httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(expected_data)}]
                        }
                    }
                ]
            },
        )
    )

    provider = GeminiProvider(api_key="mock-gemini-key", model="gemini-1.5-flash")
    result = await provider.extract_json("Extract skills from: PostgreSQL")

    assert mock_route.called
    assert result == expected_data
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
@respx.mock
async def test_gemini_embed_single_and_batch() -> None:
    single_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "text-embedding-004:embedContent"
    )
    single_route = respx.post(single_url).mock(
        return_value=httpx.Response(
            200,
            json={"embedding": {"values": [0.1, 0.2, 0.3]}},
        )
    )

    batch_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "text-embedding-004:batchEmbedContents"
    )
    batch_route = respx.post(batch_url).mock(
        return_value=httpx.Response(
            200,
            json={
                "embeddings": [
                    {"values": [0.1, 0.2, 0.3]},
                    {"values": [0.4, 0.5, 0.6]},
                ]
            },
        )
    )

    provider = GeminiProvider(api_key="mock-key", embed_model="text-embedding-004")
    single_vec = await provider.embed("Python programming")
    assert single_route.called
    assert single_vec == [0.1, 0.2, 0.3]

    batch_vecs = await provider.embed(["Python", "Rust"])
    assert batch_route.called
    assert len(batch_vecs) == 2


@pytest.mark.asyncio
@respx.mock
async def test_gemini_rate_limit_and_auth_error() -> None:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent"
    )
    respx.post(url).mock(return_value=httpx.Response(401, text="API key not valid"))

    provider = GeminiProvider(api_key="bad-key")
    with pytest.raises(InvalidAPIKeyError, match="authentication failed"):
        await provider.extract_json("test")


# ---------------------------------------------------------------------------
# GroqProvider Mocked Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_groq_extract_json_success() -> None:
    expected_data = {"technologies": ["FastAPI", "SQLAlchemy"]}
    mock_route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(expected_data)
                        }
                    }
                ]
            },
        )
    )

    provider = GroqProvider(api_key="gsk-mock-key", model="llama-3.3-70b-versatile")
    result = await provider.extract_json("Extract tech stack from: FastAPI")

    assert mock_route.called
    assert result == expected_data
    assert isinstance(provider, LLMProvider)


@pytest.mark.asyncio
@respx.mock
async def test_groq_embed_success() -> None:
    mock_route = respx.post("https://api.groq.com/openai/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.5, 0.6, 0.7]}
                ]
            },
        )
    )

    provider = GroqProvider(api_key="gsk-mock-key")
    vec = await provider.embed("Software engineering")
    assert mock_route.called
    assert vec == [0.5, 0.6, 0.7]


# ---------------------------------------------------------------------------
# Retry and Backoff Behavior Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_after_transient_failures() -> None:
    calls = 0

    async def flaky_call() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RateLimitError("Rate limit", retry_after=0.01)
        return {"status": "ok"}

    result = await execute_with_retry(
        flaky_call,
        max_retries=3,
        base_delay=0.01,
        provider_name="TestRetry",
    )
    assert result == {"status": "ok"}
    assert calls == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhausted() -> None:
    async def always_fails() -> None:
        raise ProviderUnavailableError("Down")

    with pytest.raises(ProviderUnavailableError, match="Down"):
        await execute_with_retry(
            always_fails,
            max_retries=2,
            base_delay=0.01,
            provider_name="TestExhaust",
        )


# ---------------------------------------------------------------------------
# Factory and Environment Swap Tests
# ---------------------------------------------------------------------------


def test_provider_factory_and_environment_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Explicit provider selection
    gemini = get_llm_provider("gemini")
    assert isinstance(gemini, GeminiProvider)
    assert gemini.provider_name == "gemini"

    groq = get_llm_provider("groq")
    assert isinstance(groq, GroqProvider)
    assert groq.provider_name == "groq"

    # Environment-only swap
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    env_provider = get_llm_provider()
    assert isinstance(env_provider, GroqProvider)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    env_provider2 = get_llm_provider()
    assert isinstance(env_provider2, GeminiProvider)

    # Invalid provider
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm_provider("anthropic")

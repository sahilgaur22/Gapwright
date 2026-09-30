import asyncio
import json
import logging
import re
from collections.abc import Callable, Coroutine
from typing import Any, Protocol, runtime_checkable

import httpx

from app.services.llm.exceptions import (
    ModelResponseError,
    ProviderUnavailableError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


def parse_json_from_llm_response(text: str) -> dict[str, Any] | list[Any]:
    """Extract and parse JSON from an LLM response string.

    Handles raw JSON as well as responses wrapped in markdown codeblocks.
    """
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        snippet = text[:200]
        raise ModelResponseError(
            f"Failed to decode JSON from model response: {exc}. "
            f"Response text: {snippet}"
        ) from exc

    if not isinstance(data, (dict, list)):
        raise ModelResponseError(
            f"Expected JSON object or array, got {type(data).__name__}"
        )

    return data


async def execute_with_retry[T](
    coro_fn: Callable[[], Coroutine[Any, Any, T]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    provider_name: str = "LLM",
) -> T:
    """Execute an async operation with exponential backoff for rate limits and

    transient network errors.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await coro_fn()
        except RateLimitError as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(
                    f"{provider_name} rate limit reached after {max_retries} retries"
                )
                raise

            delay = (
                exc.retry_after
                if exc.retry_after is not None
                else min(base_delay * (2**attempt), max_delay)
            )
            logger.warning(
                f"{provider_name} rate limited. Retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}/{max_retries})..."
            )
            await asyncio.sleep(delay)

        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            ProviderUnavailableError,
        ) as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(
                    f"{provider_name} request failed after {max_retries} retries: {exc}"
                )
                if isinstance(exc, ProviderUnavailableError):
                    raise
                raise ProviderUnavailableError(
                    f"{provider_name} service unavailable: {exc}"
                ) from exc

            delay = min(base_delay * (2**attempt), max_delay)
            logger.warning(
                f"{provider_name} transient error ({exc}). Retrying in {delay:.2f}s "
                f"(attempt {attempt + 1}/{max_retries})..."
            )
            await asyncio.sleep(delay)

    if last_exc:
        raise last_exc
    raise ProviderUnavailableError(f"{provider_name} execution failed")


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the standard interface for LLM providers."""

    @property
    def provider_name(self) -> str:
        """The identifier name of the provider (e.g. 'gemini', 'groq')."""
        ...

    @property
    def model_name(self) -> str:
        """The model being used for generation."""
        ...

    async def extract_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        """Send a prompt to the model and return structured JSON."""
        ...

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        """Compute embedding vectors for the given text or batch of texts."""
        ...

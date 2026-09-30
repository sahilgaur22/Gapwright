from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import (
    LLMProvider,
    execute_with_retry,
    parse_json_from_llm_response,
)
from app.services.llm.exceptions import (
    InvalidAPIKeyError,
    ModelResponseError,
    ProviderUnavailableError,
    RateLimitError,
)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_EMBED_MODEL = "text-embedding-3-small"


class GroqProvider:
    """Groq API provider for fast Llama inference and JSON extraction."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        embed_model: str | None = None,
        client: httpx.AsyncClient | None = None,
        embed_provider: LLMProvider | None = None,
    ) -> None:
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.LLM_MODEL or DEFAULT_GROQ_MODEL
        self.embed_model = (
            embed_model or settings.EMBED_MODEL or DEFAULT_GROQ_EMBED_MODEL
        )
        self._client = client
        self.embed_provider = embed_provider

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self.model

    def _ensure_api_key(self) -> str:
        if not self.api_key:
            raise InvalidAPIKeyError(
                "Groq API key not configured. Set GROQ_API_KEY in environment."
            )
        return self.api_key

    def _handle_response_status(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = float(retry_after_header) if retry_after_header else None
            raise RateLimitError("Groq rate limit exceeded", retry_after=retry_after)
        if response.status_code in (401, 403):
            raise InvalidAPIKeyError(f"Groq authentication failed: {response.text}")
        if response.status_code >= 500:
            raise ProviderUnavailableError(
                f"Groq service unavailable ({response.status_code}): {response.text}"
            )
        if response.is_error:
            raise ModelResponseError(
                f"Groq API error ({response.status_code}): {response.text}"
            )

    async def _send_extract_request(
        self,
        prompt: str,
        system_instruction: str | None,
        temperature: float,
    ) -> dict[str, Any] | list[Any]:
        api_key = self._ensure_api_key()
        url = f"{GROQ_BASE_URL}/chat/completions"

        messages: list[dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        else:
            messages.append(
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Output valid JSON.",
                }
            )
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(url, headers=headers, json=body, timeout=30.0)

        if self._client:
            resp = await _call(self._client)
        else:
            async with httpx.AsyncClient() as client:
                resp = await _call(client)

        self._handle_response_status(resp)
        data = resp.json()

        try:
            choices = data.get("choices", [])
            if not choices:
                raise ModelResponseError("Groq returned empty choices")
            content = choices[0].get("message", {}).get("content", "")
        except (KeyError, IndexError) as exc:
            raise ModelResponseError(f"Malformed Groq response: {exc}") from exc

        return parse_json_from_llm_response(content)

    async def extract_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        return await execute_with_retry(
            lambda: self._send_extract_request(prompt, system_instruction, temperature),
            max_retries=max_retries,
            provider_name="Groq",
        )

    async def _send_embeddings_request(
        self, text_input: str | list[str]
    ) -> list[float] | list[list[float]]:
        api_key = self._ensure_api_key()
        url = f"{GROQ_BASE_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.embed_model,
            "input": text_input,
        }

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(url, headers=headers, json=body, timeout=30.0)

        if self._client:
            resp = await _call(self._client)
        else:
            async with httpx.AsyncClient() as client:
                resp = await _call(client)

        self._handle_response_status(resp)
        data = resp.json()
        items = data.get("data", [])
        if not items:
            raise ModelResponseError("Embedding response contained no data")

        if isinstance(text_input, str):
            return list(items[0].get("embedding", []))
        return [list(item.get("embedding", [])) for item in items]

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        if self.embed_provider:
            return await self.embed_provider.embed(text, max_retries=max_retries)

        return await execute_with_retry(
            lambda: self._send_embeddings_request(text),
            max_retries=max_retries,
            provider_name="Groq-Embed",
        )

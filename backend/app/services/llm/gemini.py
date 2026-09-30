from typing import Any

import httpx

from app.core.config import settings
from app.services.llm.base import execute_with_retry, parse_json_from_llm_response
from app.services.llm.exceptions import (
    InvalidAPIKeyError,
    ModelResponseError,
    ProviderUnavailableError,
    RateLimitError,
)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_EMBED_MODEL = "text-embedding-004"


class GeminiProvider:
    """Gemini API provider for structured JSON extraction and vector embeddings."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        embed_model: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.LLM_MODEL or DEFAULT_GEMINI_MODEL
        self.embed_model = embed_model or settings.EMBED_MODEL or DEFAULT_EMBED_MODEL
        self._client = client

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.model

    def _ensure_api_key(self) -> str:
        if not self.api_key:
            raise InvalidAPIKeyError(
                "Gemini API key not configured. Set GEMINI_API_KEY in environment."
            )
        return self.api_key

    def _handle_response_status(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = float(retry_after_header) if retry_after_header else None
            raise RateLimitError("Gemini rate limit exceeded", retry_after=retry_after)
        if response.status_code in (401, 403):
            raise InvalidAPIKeyError(f"Gemini authentication failed: {response.text}")
        if response.status_code >= 500:
            raise ProviderUnavailableError(
                f"Gemini service unavailable ({response.status_code}): {response.text}"
            )
        if response.is_error:
            raise ModelResponseError(
                f"Gemini API error ({response.status_code}): {response.text}"
            )

    async def _send_extract_request(
        self,
        prompt: str,
        system_instruction: str | None,
        temperature: float,
    ) -> dict[str, Any] | list[Any]:
        api_key = self._ensure_api_key()
        url = f"{GEMINI_BASE_URL}/models/{self.model}:generateContent"

        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature,
            },
        }

        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                url,
                params={"key": api_key},
                json=body,
                timeout=30.0,
            )

        if self._client:
            resp = await _call(self._client)
        else:
            async with httpx.AsyncClient() as client:
                resp = await _call(client)

        self._handle_response_status(resp)
        data = resp.json()

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ModelResponseError("Gemini returned empty candidates")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ModelResponseError("Gemini returned no content parts")
            text_content = parts[0].get("text", "")
        except (KeyError, IndexError) as exc:
            raise ModelResponseError(
                f"Malformed Gemini response payload: {exc}"
            ) from exc

        return parse_json_from_llm_response(text_content)

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
            provider_name="Gemini",
        )

    async def _send_single_embed(self, text: str) -> list[float]:
        api_key = self._ensure_api_key()
        url = f"{GEMINI_BASE_URL}/models/{self.embed_model}:embedContent"
        body = {"content": {"parts": [{"text": text}]}}

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                url,
                params={"key": api_key},
                json=body,
                timeout=30.0,
            )

        if self._client:
            resp = await _call(self._client)
        else:
            async with httpx.AsyncClient() as client:
                resp = await _call(client)

        self._handle_response_status(resp)
        data = resp.json()
        values: list[float] = data.get("embedding", {}).get("values", [])
        if not values:
            raise ModelResponseError("Gemini returned empty embedding values")
        return values

    async def _send_batch_embed(self, texts: list[str]) -> list[list[float]]:
        api_key = self._ensure_api_key()
        url = f"{GEMINI_BASE_URL}/models/{self.embed_model}:batchEmbedContents"
        body = {
            "requests": [
                {
                    "model": f"models/{self.embed_model}",
                    "content": {"parts": [{"text": t}]},
                }
                for t in texts
            ]
        }

        async def _call(client: httpx.AsyncClient) -> httpx.Response:
            return await client.post(
                url,
                params={"key": api_key},
                json=body,
                timeout=30.0,
            )

        if self._client:
            resp = await _call(self._client)
        else:
            async with httpx.AsyncClient() as client:
                resp = await _call(client)

        self._handle_response_status(resp)
        data = resp.json()
        raw_embeddings = data.get("embeddings", [])
        return [item.get("values", []) for item in raw_embeddings]

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        if isinstance(text, str):
            return await execute_with_retry(
                lambda: self._send_single_embed(text),
                max_retries=max_retries,
                provider_name="Gemini-Embed",
            )
        return await execute_with_retry(
            lambda: self._send_batch_embed(text),
            max_retries=max_retries,
            provider_name="Gemini-Embed-Batch",
        )

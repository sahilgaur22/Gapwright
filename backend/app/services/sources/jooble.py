import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.services.sources.base import BaseJobSource
from app.services.sources.limiter import rate_limiter
from app.services.sources.models import RawJob

logger = logging.getLogger(__name__)


def _parse_jooble_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        # Jooble emits format like "2026-09-29T11:45:00.0000000" or ISO
        clean = val.rstrip("Z")
        # Python fromisoformat handles up to 6 microsecond digits
        if "." in clean:
            base, frac = clean.split(".", 1)
            frac = frac[:6]
            clean = f"{base}.{frac}"
        dt = datetime.fromisoformat(clean)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


class JoobleSource(BaseJobSource):
    """Job data source connector for Jooble POST API (Priority P1)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://jooble.org/api",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        page_size: int = 20,
    ) -> None:
        self.api_key = api_key or settings.JOOBLE_API_KEY
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.page_size = page_size

    @property
    def name(self) -> str:
        return "jooble"

    @property
    def priority(self) -> int:
        return 1

    @property
    def default_daily_budget(self) -> int:
        return settings.JOOBLE_DAILY_BUDGET

    @property
    def attribution_text(self) -> str:
        return "Jobs via Jooble"

    @property
    def attribution_url(self) -> str:
        return "https://jooble.org"

    @property
    def may_display_listing(self) -> bool:
        return True

    def _map_result_to_raw_job(self, item: dict[str, Any]) -> RawJob | None:
        """Map a single Jooble job object to RawJob."""
        raw_id = item.get("id")
        title = item.get("title")
        description = item.get("snippet") or item.get("description")

        if not raw_id or not title or not description:
            return None

        company = item.get("company")
        location = item.get("location")
        posted_at = _parse_jooble_datetime(item.get("updated"))

        return RawJob(
            source=self.name,
            external_id=str(raw_id),
            title=str(title).strip(),
            company=str(company).strip() if company else None,
            location=str(location).strip() if location else None,
            description=str(description).strip(),
            description_is_truncated=True,  # Jooble returns snippets
            url=item.get("link"),
            posted_at=posted_at,
            attribution_text=self.attribution_text,
            attribution_url=self.attribution_url,
            may_display_listing=self.may_display_listing,
        )

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        page: int,
        role: str,
        location: str | None,
        results_per_page: int,
    ) -> dict[str, Any] | None:
        """Execute POST request for a page with retries and rate limiting."""
        endpoint = f"{self.base_url}/{self.api_key}"
        payload: dict[str, Any] = {
            "keywords": role,
            "page": page,
            "resultonpage": results_per_page,
        }
        if location:
            payload["location"] = location

        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }

        for attempt in range(self.max_retries):
            await rate_limiter.acquire("jooble.org")
            try:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, dict) else None

                if (
                    response.status_code in (429, 500, 502, 503, 504)
                    and attempt < self.max_retries - 1
                ):
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        f"Jooble status {response.status_code}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue

                logger.error(
                    f"Jooble request failed with status {response.status_code}: "
                    f"{response.text}"
                )
                return None

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        f"Jooble network error ({exc}). "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                logger.error(
                    f"Jooble connection failed after {self.max_retries} attempts: {exc}"
                )
                return None

        return None

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[RawJob]:
        """Search Jooble job listings via POST API, handling missing key gracefully."""
        if not self.api_key:
            logger.info(
                "Jooble API key not yet issued or configured "
                "(JOOBLE_API_KEY unset). Source 'jooble' is disabled."
            )
            return []

        results: list[RawJob] = []
        page = 1
        results_per_page = min(self.page_size, 50)
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        async def _run_search(client: httpx.AsyncClient) -> list[RawJob]:
            nonlocal page
            while len(results) < limit:
                page_data = await self._fetch_page(
                    client=client,
                    page=page,
                    role=role,
                    location=location,
                    results_per_page=results_per_page,
                )

                if not page_data or "jobs" not in page_data:
                    break

                raw_items = page_data.get("jobs", [])
                if not raw_items or not isinstance(raw_items, list):
                    break

                for item in raw_items:
                    if isinstance(item, dict):
                        job = self._map_result_to_raw_job(item)
                        if job:
                            # Filter postings older than since cutoff
                            if (
                                since_utc
                                and job.posted_at
                                and job.posted_at < since_utc
                            ):
                                continue
                            results.append(job)
                            if len(results) >= limit:
                                break

                if len(raw_items) < results_per_page or len(results) >= limit:
                    break

                page += 1

            return results

        if http_client is not None:
            return await _run_search(http_client)

        async with httpx.AsyncClient() as client:
            return await _run_search(client)

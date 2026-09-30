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


def _parse_iso_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        # Standard ISO 8601, e.g. "2026-09-28T08:30:00Z"
        clean = val.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


class AdzunaSource(BaseJobSource):
    """Job data source connector for Adzuna REST API (Priority P1)."""

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        country: str | None = None,
        base_url: str = "https://api.adzuna.com/v1/api/jobs",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        page_size: int = 50,
    ) -> None:
        self.app_id = app_id or settings.ADZUNA_APP_ID
        self.app_key = app_key or settings.ADZUNA_APP_KEY
        self.country = (country or settings.ADZUNA_COUNTRY or "in").lower()
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.page_size = page_size

    @property
    def name(self) -> str:
        return "adzuna"

    @property
    def priority(self) -> int:
        return 1

    @property
    def default_daily_budget(self) -> int:
        return settings.ADZUNA_DAILY_BUDGET

    @property
    def attribution_text(self) -> str:
        return "Powered by Adzuna"

    @property
    def attribution_url(self) -> str:
        return "https://www.adzuna.com"

    @property
    def may_display_listing(self) -> bool:
        return True

    def _map_result_to_raw_job(self, item: dict[str, Any]) -> RawJob | None:
        """Map a single Adzuna API result dictionary to RawJob."""
        raw_id = item.get("id")
        title = item.get("title")
        description = item.get("description")

        if not raw_id or not title or not description:
            return None

        company_dict = item.get("company") or {}
        company = (
            company_dict.get("display_name")
            if isinstance(company_dict, dict)
            else None
        )

        location_dict = item.get("location") or {}
        location = (
            location_dict.get("display_name")
            if isinstance(location_dict, dict)
            else None
        )

        posted_at = _parse_iso_datetime(item.get("created"))

        return RawJob(
            source=self.name,
            external_id=str(raw_id),
            title=title.strip(),
            company=company.strip() if company else None,
            location=location.strip() if location else None,
            description=description.strip(),
            description_is_truncated=True,  # Adzuna results only supply excerpts
            url=item.get("redirect_url"),
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
        max_days_old: int,
        results_per_page: int,
    ) -> dict[str, Any] | None:
        """Fetch a single page of results with retries and rate limiting."""
        endpoint = f"{self.base_url}/{self.country}/search/{page}"
        params: dict[str, Any] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": role,
            "sort_by": "date",
            "max_days_old": max_days_old,
            "results_per_page": results_per_page,
        }
        if location:
            params["where"] = location

        headers = {"User-Agent": self.user_agent}

        for attempt in range(self.max_retries):
            # Enforce polite domain rate limiting
            await rate_limiter.acquire("api.adzuna.com")
            try:
                response = await client.get(
                    endpoint,
                    params=params,
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
                        f"Adzuna status {response.status_code}. "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue

                logger.error(
                    f"Adzuna request failed with status {response.status_code}: "
                    f"{response.text}"
                )
                return None

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        f"Adzuna network error ({exc}). "
                        f"Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)
                    continue
                logger.error(
                    f"Adzuna connection failed after {self.max_retries} attempts: {exc}"
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
        """Search Adzuna job listings for role and optional location."""
        if not self.app_id or not self.app_key:
            logger.warning(
                "Adzuna credentials not configured. Skipping source."
            )
            return []

        # Determine age cutoff
        if since is not None:
            now = datetime.now(UTC)
            since_utc = since if since.tzinfo else since.replace(tzinfo=UTC)
            delta = now - since_utc
            max_days_old = max(1, delta.days)
        else:
            max_days_old = settings.ANALYSIS_WINDOW_DAYS

        results: list[RawJob] = []
        page = 1
        results_per_page = min(self.page_size, 50)

        # Context manager for client
        async def _run_search(client: httpx.AsyncClient) -> list[RawJob]:
            nonlocal page
            while len(results) < limit:
                page_data = await self._fetch_page(
                    client=client,
                    page=page,
                    role=role,
                    location=location,
                    max_days_old=max_days_old,
                    results_per_page=results_per_page,
                )

                if not page_data or "results" not in page_data:
                    break

                raw_items = page_data.get("results", [])
                if not raw_items or not isinstance(raw_items, list):
                    break

                for item in raw_items:
                    if isinstance(item, dict):
                        job = self._map_result_to_raw_job(item)
                        if job:
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

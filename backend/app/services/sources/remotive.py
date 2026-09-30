import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.services.sources.base import BaseJobSource
from app.services.sources.limiter import rate_limiter
from app.services.sources.models import RawJob
from app.services.sources.utils import clean_html, parse_iso_datetime

logger = logging.getLogger(__name__)


class RemotiveSource(BaseJobSource):
    """Job data source connector for Remotive Public JSON API (Priority P2).

    Terms: Max 4 fetches/day, data is delayed ~24h, must not republish listing text
    to third-party sites (may_display_listing=False).
    """

    def __init__(
        self,
        base_url: str = "https://remotive.com/api/remote-jobs",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @property
    def name(self) -> str:
        return "remotive"

    @property
    def priority(self) -> int:
        return 2

    @property
    def default_daily_budget(self) -> int:
        # Remotive docs advise maximum 4 fetches per day
        return 4

    @property
    def attribution_text(self) -> str:
        return "Data from Remotive"

    @property
    def attribution_url(self) -> str:
        return "https://remotive.com"

    @property
    def may_display_listing(self) -> bool:
        # Terms require internal skill statistics only; no republication of full text
        return False

    def _map_job(self, item: dict[str, Any]) -> RawJob | None:
        raw_id = item.get("id")
        title = item.get("title")
        raw_desc = item.get("description")

        if not raw_id or not title:
            return None

        posted_at = parse_iso_datetime(item.get("publication_date"))

        return RawJob(
            source=self.name,
            external_id=str(raw_id),
            title=str(title).strip(),
            company=str(item.get("company_name", "")).strip() or None,
            location=str(item.get("candidate_required_location", "Remote")).strip(),
            description=clean_html(raw_desc),
            description_is_truncated=False,
            url=item.get("url"),
            posted_at=posted_at,
            attribution_text=self.attribution_text,
            attribution_url=self.attribution_url,
            may_display_listing=self.may_display_listing,
        )

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[RawJob]:
        """Query Remotive remote jobs matching role keyword and since cutoff."""
        params: dict[str, Any] = {}
        if role:
            params["search"] = role
        if limit:
            params["limit"] = min(limit, 100)

        headers = {"User-Agent": self.user_agent}
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        async def _fetch(client: httpx.AsyncClient) -> list[RawJob]:
            for attempt in range(self.max_retries):
                await rate_limiter.acquire("remotive.com")
                try:
                    response = await client.get(
                        self.base_url,
                        params=params,
                        headers=headers,
                        timeout=15.0,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        raw_jobs = (
                            data.get("jobs", []) if isinstance(data, dict) else []
                        )
                        results: list[RawJob] = []
                        for item in raw_jobs:
                            if isinstance(item, dict):
                                job = self._map_job(item)
                                if job:
                                    if (
                                        since_utc
                                        and job.posted_at
                                        and job.posted_at < since_utc
                                    ):
                                        continue
                                    results.append(job)
                                    if len(results) >= limit:
                                        break
                        return results

                    if (
                        response.status_code in (429, 500, 502, 503, 504)
                        and attempt < self.max_retries - 1
                    ):
                        sleep_time = self.backoff_factor * (2**attempt)
                        logger.warning(
                            f"Remotive status {response.status_code}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    logger.error(f"Remotive request failed: {response.status_code}")
                    return []

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_factor * (2**attempt)
                        logger.warning(
                            f"Remotive network error ({exc}). "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue
                    logger.error(
                        f"Remotive failed after {self.max_retries} attempts: {exc}"
                    )
                    return []

            return []

        if http_client is not None:
            return await _fetch(http_client)

        async with httpx.AsyncClient() as client:
            return await _fetch(client)

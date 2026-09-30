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


class RemoteOKSource(BaseJobSource):
    """Job data source connector for RemoteOK Public JSON API (Priority P2).

    Terms: Politeness delay >= 500ms, requires follow backlink to remoteok.com,
    first JSON element contains legal metadata and must be skipped.
    """

    def __init__(
        self,
        base_url: str = "https://remoteok.com/api",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @property
    def name(self) -> str:
        return "remoteok"

    @property
    def priority(self) -> int:
        return 2

    @property
    def default_daily_budget(self) -> int:
        # 1 fetch per 6h = 4 per day
        return 4

    @property
    def min_delay_seconds(self) -> float:
        # RemoteOK terms require >= 500ms politeness delay
        return 0.5

    @property
    def attribution_text(self) -> str:
        return "Jobs by RemoteOK"

    @property
    def attribution_url(self) -> str:
        return "https://remoteok.com"

    @property
    def may_display_listing(self) -> bool:
        return True

    def _map_job(self, item: dict[str, Any]) -> RawJob | None:
        # RemoteOK passes legal object as first element; skip it
        if "legal" in item or "terms" in item or not item.get("id"):
            return None

        raw_id = item.get("id")
        title = item.get("position") or item.get("title")
        if not raw_id or not title:
            return None

        posted_at = parse_iso_datetime(item.get("date"))

        # Build url if only slug is provided
        url = item.get("url")
        if not url and item.get("slug"):
            url = f"https://remoteok.com/remote-jobs/{item['slug']}"

        return RawJob(
            source=self.name,
            external_id=str(raw_id),
            title=str(title).strip(),
            company=str(item.get("company", "")).strip() or None,
            location=str(item.get("location", "Worldwide")).strip(),
            description=clean_html(item.get("description")),
            description_is_truncated=False,
            url=url,
            posted_at=posted_at,
            attribution_text=self.attribution_text,
            attribution_url=self.attribution_url,
            may_display_listing=self.may_display_listing,
        )

    def _matches_role(self, job: RawJob, item: dict[str, Any], role: str) -> bool:
        """Check if job matches role keyword via title, tags, or description."""
        if not role:
            return True
        r = role.lower().strip()
        if r in job.title.lower():
            return True
        tags = item.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if r in str(tag).lower():
                    return True
        return False

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[RawJob]:
        """Fetch RemoteOK feed, skipping legal preamble and filtering by role/since."""
        headers = {"User-Agent": self.user_agent}
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        async def _fetch(client: httpx.AsyncClient) -> list[RawJob]:
            for attempt in range(self.max_retries):
                # Acquire rate limiter honoring >= 500ms delay
                await rate_limiter.acquire("remoteok.com")
                try:
                    response = await client.get(
                        self.base_url,
                        headers=headers,
                        timeout=15.0,
                    )
                    if response.status_code == 200:
                        raw_data = response.json()
                        if not isinstance(raw_data, list):
                            return []

                        results: list[RawJob] = []
                        for item in raw_data:
                            if not isinstance(item, dict):
                                continue
                            # Skips legal object
                            job = self._map_job(item)
                            if job is None:
                                continue

                            # Apply keyword filter
                            if not self._matches_role(job, item, role):
                                continue

                            # Apply since cutoff
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
                            f"RemoteOK status {response.status_code}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    logger.error(f"RemoteOK request failed: {response.status_code}")
                    return []

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_factor * (2**attempt)
                        logger.warning(
                            f"RemoteOK network error ({exc}). "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue
                    logger.error(
                        f"RemoteOK failed after {self.max_retries} attempts: {exc}"
                    )
                    return []

            return []

        if http_client is not None:
            return await _fetch(http_client)

        async with httpx.AsyncClient() as client:
            return await _fetch(client)

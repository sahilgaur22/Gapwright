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


class ArbeitnowSource(BaseJobSource):
    """Job data source connector for Arbeitnow API (Priority P3).

    Disabled by default; covers European and remote tech postings.
    """

    def __init__(
        self,
        base_url: str = "https://www.arbeitnow.com/api/job-board-api",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        user_agent: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._custom_user_agent = user_agent

    @property
    def user_agent(self) -> str:
        return self._custom_user_agent or super().user_agent

    @property
    def name(self) -> str:
        return "arbeitnow"

    @property
    def priority(self) -> int:
        return 3

    @property
    def default_daily_budget(self) -> int:
        return 24

    @property
    def attribution_text(self) -> str:
        return "Jobs by Arbeitnow"

    @property
    def attribution_url(self) -> str:
        return "https://www.arbeitnow.com"

    @property
    def may_display_listing(self) -> bool:
        return True

    def _map_job(self, item: dict[str, Any]) -> RawJob | None:
        slug = item.get("slug")
        title = item.get("title")
        if not slug or not title:
            return None

        # Determine posted date (integer epoch or ISO string)
        created_val = item.get("created_at")
        posted_at: datetime | None = None
        if isinstance(created_val, (int, float)):
            try:
                posted_at = datetime.fromtimestamp(created_val, tz=UTC)
            except (ValueError, OSError):
                posted_at = None
        elif isinstance(created_val, str):
            posted_at = parse_iso_datetime(created_val)

        loc = str(item.get("location", "")).strip()
        if not loc and item.get("remote"):
            loc = "Remote"
        elif not loc:
            loc = "Unknown"

        url = item.get("url") or f"https://www.arbeitnow.com/jobs/{slug}"

        return RawJob(
            source=self.name,
            external_id=str(slug).strip(),
            title=str(title).strip(),
            company=str(item.get("company_name", "")).strip() or None,
            location=loc,
            description=clean_html(item.get("description")),
            description_is_truncated=False,
            url=url,
            posted_at=posted_at,
            attribution_text=self.attribution_text,
            attribution_url=self.attribution_url,
            may_display_listing=self.may_display_listing,
        )

    def _matches_role(self, job: RawJob, item: dict[str, Any], role: str) -> bool:
        if not role:
            return True
        r = role.lower().strip()
        if r in job.title.lower() or r in job.description.lower():
            return True
        tags = item.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if r in str(tag).lower():
                    return True
        return False

    def _matches_location(self, job: RawJob, location: str | None) -> bool:
        if not location:
            return True
        loc = location.lower().strip()
        job_loc = (job.location or "").lower()
        return loc in job_loc

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[RawJob]:
        """Fetch Arbeitnow listings, filtering client-side by role and location."""
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        async def _fetch(client: httpx.AsyncClient) -> list[RawJob]:
            for attempt in range(self.max_retries):
                await rate_limiter.acquire("arbeitnow.com")
                try:
                    response = await client.get(
                        self.base_url,
                        headers=headers,
                        timeout=15.0,
                    )
                    if response.status_code == 200:
                        body = response.json()
                        raw_data = (
                            body.get("data", []) if isinstance(body, dict) else []
                        )
                        results: list[RawJob] = []

                        for item in raw_data:
                            if not isinstance(item, dict):
                                continue
                            job = self._map_job(item)
                            if job is None:
                                continue

                            if not self._matches_role(job, item, role):
                                continue
                            if not self._matches_location(job, location):
                                continue

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
                            f"Arbeitnow status {response.status_code}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    logger.error(f"Arbeitnow request failed: {response.status_code}")
                    return []

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_factor * (2**attempt)
                        logger.warning(
                            f"Arbeitnow error ({exc}). Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue
                    logger.error(
                        f"Arbeitnow connection failed after "
                        f"{self.max_retries} attempts: {exc}"
                    )
                    return []

            return []

        if http_client is not None:
            return await _fetch(http_client)
        async with httpx.AsyncClient() as client:
            return await _fetch(client)

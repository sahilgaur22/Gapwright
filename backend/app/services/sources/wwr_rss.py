import asyncio
import calendar
import logging
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from app.services.sources.base import BaseJobSource
from app.services.sources.limiter import rate_limiter
from app.services.sources.models import RawJob
from app.services.sources.utils import clean_html

logger = logging.getLogger(__name__)


def _extract_company_and_title(raw_title: str) -> tuple[str | None, str]:
    """WWR RSS titles usually follow the format 'Company: Job Title'."""
    if ":" in raw_title:
        company_part, title_part = raw_title.split(":", 1)
        return company_part.strip() or None, title_part.strip()
    return None, raw_title.strip()


class WeWorkRemotelyRSSSource(BaseJobSource):
    """Job data source connector for We Work Remotely Public RSS feeds (Priority P2)."""

    def __init__(
        self,
        feed_url: str = "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.feed_url = feed_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    @property
    def name(self) -> str:
        return "wwr_rss"

    @property
    def priority(self) -> int:
        return 2

    @property
    def default_daily_budget(self) -> int:
        # 1 fetch per 6h = 4 per day
        return 4

    @property
    def attribution_text(self) -> str:
        return "Jobs via We Work Remotely"

    @property
    def attribution_url(self) -> str:
        return "https://weworkremotely.com"

    @property
    def may_display_listing(self) -> bool:
        return True

    def _map_entry(self, entry: Any) -> RawJob | None:
        raw_id = entry.get("id") or entry.get("guid") or entry.get("link")
        raw_title = entry.get("title")

        if not raw_id or not raw_title:
            return None

        company, title = _extract_company_and_title(str(raw_title))

        posted_at: datetime | None = None
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            try:
                timestamp = calendar.timegm(published_parsed)
                posted_at = datetime.fromtimestamp(timestamp, tz=UTC)
            except Exception:
                posted_at = None

        raw_desc = entry.get("summary") or entry.get("description") or ""

        return RawJob(
            source=self.name,
            external_id=str(raw_id),
            title=title,
            company=company,
            location="Remote",
            description=clean_html(raw_desc),
            description_is_truncated=False,
            url=entry.get("link"),
            posted_at=posted_at,
            attribution_text=self.attribution_text,
            attribution_url=self.attribution_url,
            may_display_listing=self.may_display_listing,
        )

    def _matches_role(self, job: RawJob, role: str) -> bool:
        if not role:
            return True
        r = role.lower().strip()
        return r in job.title.lower() or r in job.description.lower()

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[RawJob]:
        """Fetch and parse WWR RSS feed, filtering by role and cutoff date."""
        headers = {"User-Agent": self.user_agent}
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        async def _fetch(client: httpx.AsyncClient) -> list[RawJob]:
            for attempt in range(self.max_retries):
                await rate_limiter.acquire("weworkremotely.com")
                try:
                    response = await client.get(
                        self.feed_url,
                        headers=headers,
                        timeout=15.0,
                    )
                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        results: list[RawJob] = []

                        for entry in feed.entries:
                            job = self._map_entry(entry)
                            if job is None:
                                continue

                            if not self._matches_role(job, role):
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
                            f"WWR status {response.status_code}. "
                            f"Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    logger.error(f"WWR RSS request failed: {response.status_code}")
                    return []

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    if attempt < self.max_retries - 1:
                        sleep_time = self.backoff_factor * (2**attempt)
                        logger.warning(
                            f"WWR error ({exc}). Retrying in {sleep_time:.2f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue
                    logger.error(
                        f"WWR RSS failed after {self.max_retries} attempts: {exc}"
                    )
                    return []

            return []

        if http_client is not None:
            return await _fetch(http_client)

        async with httpx.AsyncClient() as client:
            return await _fetch(client)

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


def _extract_hn_job_metadata(clean_text: str) -> tuple[str | None, str, str]:
    """Parse company, title, and location heuristics from HN hiring comment.

    HN hiring comments conventionally open with pipe-separated metadata:
    "Stripe | Infrastructure Engineer | San Francisco, CA | Full-time | REMOTE"
    """
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    if not lines:
        return None, "Software Engineer", "Remote"

    first_line = lines[0]
    if "|" in first_line:
        parts = [p.strip() for p in first_line.split("|")]
        company = parts[0] if parts else None
        title = parts[1] if len(parts) > 1 else "Engineer"
        location = parts[2] if len(parts) > 2 else "Remote"
        return company, title, location

    return None, first_line[:60], "Remote"


class HNHiringSource(BaseJobSource):
    """Job source connector for Hacker News monthly 'Who is hiring' threads.

    Powered by Algolia's official public Hacker News search API.
    Disabled by default (Priority P3).
    """

    def __init__(
        self,
        base_api_url: str = "https://hn.algolia.com/api/v1",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        user_agent: str | None = None,
    ) -> None:
        self.base_api_url = base_api_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._custom_user_agent = user_agent

    @property
    def user_agent(self) -> str:
        return self._custom_user_agent or super().user_agent

    @property
    def name(self) -> str:
        return "hn_hiring"

    @property
    def priority(self) -> int:
        return 3

    @property
    def default_daily_budget(self) -> int:
        return 10

    @property
    def attribution_text(self) -> str:
        return "Hacker News Who is Hiring"

    @property
    def attribution_url(self) -> str:
        return "https://news.ycombinator.com"

    @property
    def may_display_listing(self) -> bool:
        return True

    def _map_comment_to_job(self, item: dict[str, Any]) -> RawJob | None:
        object_id = item.get("objectID")
        comment_text = item.get("comment_text")
        if not object_id or not comment_text:
            return None

        cleaned = clean_html(comment_text)
        company, title, location = _extract_hn_job_metadata(cleaned)

        created_val = item.get("created_at_i")
        posted_at: datetime | None = None
        if isinstance(created_val, (int, float)):
            try:
                posted_at = datetime.fromtimestamp(created_val, tz=UTC)
            except (ValueError, OSError):
                posted_at = None
        elif item.get("created_at"):
            posted_at = parse_iso_datetime(str(item.get("created_at")))

        return RawJob(
            source=self.name,
            external_id=str(object_id).strip(),
            title=title,
            company=company,
            location=location,
            description=cleaned,
            description_is_truncated=False,
            url=f"https://news.ycombinator.com/item?id={object_id}",
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

    def _matches_location(self, job: RawJob, location: str | None) -> bool:
        if not location:
            return True
        loc = location.lower().strip()
        job_loc = (job.location or "").lower()
        return loc in job_loc or loc in job.description.lower()

    async def _find_latest_story_id(self, client: httpx.AsyncClient) -> str | None:
        """Find the story objectID of the latest 'Ask HN: Who is hiring' thread."""
        url = f"{self.base_api_url}/search_by_date"
        params: dict[str, Any] = {
            "tags": "story,author_whoishiring",
            "query": "Ask HN: Who is hiring?",
            "hitsPerPage": 1,
        }
        headers = {"User-Agent": self.user_agent}

        for attempt in range(self.max_retries):
            await rate_limiter.acquire("hn.algolia.com")
            try:
                resp = await client.get(
                    url, params=params, headers=headers, timeout=15.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    hits = data.get("hits", [])
                    if hits and isinstance(hits[0], dict):
                        return str(hits[0].get("objectID"))
                    return None
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.backoff_factor * (2**attempt))
                    continue
                logger.warning(f"Failed to find HN whoishiring story: {exc}")
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
        """Fetch comments from latest Who is hiring thread and filter by role."""
        headers = {"User-Agent": self.user_agent}
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        async def _fetch(client: httpx.AsyncClient) -> list[RawJob]:
            story_id = await self._find_latest_story_id(client)
            if not story_id:
                logger.info("No active HN Who is hiring thread found")
                return []

            url = f"{self.base_api_url}/search_by_date"
            params: dict[str, Any] = {
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": min(limit * 2, 100),
            }

            for attempt in range(self.max_retries):
                await rate_limiter.acquire("hn.algolia.com")
                try:
                    resp = await client.get(
                        url, params=params, headers=headers, timeout=15.0
                    )
                    if resp.status_code == 200:
                        body = resp.json()
                        hits = body.get("hits", [])
                        results: list[RawJob] = []

                        for item in hits:
                            if not isinstance(item, dict):
                                continue
                            job = self._map_comment_to_job(item)
                            if job is None:
                                continue

                            if not self._matches_role(job, role):
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
                        resp.status_code in (429, 500, 502, 503, 504)
                        and attempt < self.max_retries - 1
                    ):
                        await asyncio.sleep(self.backoff_factor * (2**attempt))
                        continue

                    logger.error(f"HN Algolia search failed: {resp.status_code}")
                    return []

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.backoff_factor * (2**attempt))
                        continue
                    logger.error(f"HN Algolia network error: {exc}")
                    return []

            return []

        if http_client is not None:
            return await _fetch(http_client)
        async with httpx.AsyncClient() as client:
            return await _fetch(client)

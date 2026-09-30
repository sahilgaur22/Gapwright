import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.services.sources.base import BaseJobSource
from app.services.sources.models import RawJob
from app.services.sources.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE_PATH = (
    Path(__file__).parent / "data" / "indian_jobs_fixture.json"
)


class FixtureSource(BaseJobSource):
    """Job source backed by local curated benchmark datasets.

    Used for offline tests, local development, demos, and fallbacks
    when external network/rate-limited APIs are unavailable.
    """

    def __init__(self, data_path: Path | str | None = None) -> None:
        self.data_path = Path(data_path) if data_path else DEFAULT_FIXTURE_PATH
        self._cached_jobs: list[RawJob] | None = None

    @property
    def name(self) -> str:
        return "fixture"

    @property
    def priority(self) -> int:
        return 10

    @property
    def default_daily_budget(self) -> int:
        return 10000

    @property
    def attribution_text(self) -> str:
        return "Curated sample dataset"

    @property
    def attribution_url(self) -> str | None:
        return None

    @property
    def may_display_listing(self) -> bool:
        return True

    def _load_jobs(self) -> list[RawJob]:
        """Load and parse jobs from local JSON file."""
        if self._cached_jobs is not None:
            return self._cached_jobs

        if not self.data_path.exists():
            logger.warning(f"Fixture data file not found: {self.data_path}")
            return []

        try:
            raw_text = self.data_path.read_text(encoding="utf-8")
            items = json.loads(raw_text)
            if not isinstance(items, list):
                logger.warning(f"Unexpected fixture format in {self.data_path}")
                return []

            parsed: list[RawJob] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                ext_id = str(item.get("id", "")).strip()
                title = str(item.get("title", "")).strip()
                if not ext_id or not title:
                    continue

                posted_at = parse_iso_datetime(item.get("posted_at"))
                raw_job = RawJob(
                    source=self.name,
                    external_id=ext_id,
                    title=title,
                    company=str(item.get("company", "")).strip() or None,
                    location=str(item.get("location", "India")).strip(),
                    description=str(item.get("description", "")).strip(),
                    description_is_truncated=False,
                    url=item.get("url"),
                    posted_at=posted_at,
                    attribution_text=self.attribution_text,
                    attribution_url=self.attribution_url,
                    may_display_listing=self.may_display_listing,
                )
                parsed.append(raw_job)

            self._cached_jobs = parsed
            return self._cached_jobs
        except Exception as exc:
            logger.error(f"Error loading fixture jobs from {self.data_path}: {exc}")
            return []

    def _matches_role(self, job: RawJob, role: str) -> bool:
        if not role:
            return True
        r = role.lower().strip()
        # Direct phrase match in title or description
        if r in job.title.lower() or r in job.description.lower():
            return True
        # Token match: if all significant words appear in title or description
        words = [w for w in r.split() if len(w) > 2]
        return bool(
            words
            and all(
                w in job.title.lower() or w in job.description.lower()
                for w in words
            )
        )

    def _matches_location(self, job: RawJob, location: str | None) -> bool:
        if not location:
            return True
        loc = location.lower().strip()
        job_loc = (job.location or "").lower()
        if loc in job_loc:
            return True
        indian_regions = ("india", "karnataka", "telangana", "maharashtra", "delhi")
        return loc == "india" and any(reg in job_loc for reg in indian_regions)

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[RawJob]:
        """Search curated fixture dataset offline by role keyword and location."""
        all_jobs = self._load_jobs()
        since_utc = (
            since if (since is None or since.tzinfo) else since.replace(tzinfo=UTC)
        )

        results: list[RawJob] = []
        for job in all_jobs:
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

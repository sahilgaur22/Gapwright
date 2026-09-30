from abc import ABC, abstractmethod
from datetime import datetime

from app.core.config import settings
from app.services.sources.models import RawJob


class BaseJobSource(ABC):
    """Abstract Base Class for all external job data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique source identifier (e.g. 'adzuna', 'jooble', 'remotive')."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority tier (1=P1 primary, 2=P2 remote, 3=P3 optional, 10=demo/fixture)."""
        pass

    @property
    def default_daily_budget(self) -> int:
        """Default maximum API calls or page fetches allowed per day."""
        return 50

    @property
    def min_delay_seconds(self) -> float:
        """Politeness delay in seconds between consecutive requests to this provider."""
        return 0.0

    @property
    def user_agent(self) -> str:
        """User-agent header to present for HTTP requests."""
        return settings.CRAWL_USER_AGENT

    @property
    def attribution_text(self) -> str:
        """Attribution label for display in UI."""
        return f"Jobs via {self.name.capitalize()}"

    @property
    def attribution_url(self) -> str | None:
        """Attribution link for backlinking."""
        return None

    @property
    def may_display_listing(self) -> bool:
        """Whether source terms permit displaying listing text to end-users."""
        return True

    @abstractmethod
    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[RawJob]:
        """Query jobs matching role and location published on or after since.

        Args:
            role: Target job title / role keyword query (e.g. 'Data Scientist').
            location: Target geographic location (e.g. 'Bangalore') or None for remote.
            since: Optional cutoff datetime; postings older than this can be skipped.
            limit: Maximum number of raw postings to return.

        Returns:
            List of normalized RawJob instances.
        """
        pass

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from app.core.config import settings

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Evaluates robots.txt compliance for external requests and web scraping."""

    def __init__(self) -> None:
        self._parsers: dict[str, RobotFileParser] = {}

    def set_rules(self, base_url: str, content: str) -> None:
        """Parse and store robots.txt content for a domain."""
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        parser = RobotFileParser()
        parser.parse(content.splitlines())
        self._parsers[domain] = parser

    def is_allowed(
        self,
        url: str,
        user_agent: str | None = None,
        robots_txt_content: str | None = None,
    ) -> bool:
        """Determine whether the specified URL is permitted for the user agent.

        If robots.txt content is provided, it is parsed and cached.
        If no rules have been configured for the domain, defaults to True (permissive).
        """
        ua = user_agent or settings.CRAWL_USER_AGENT
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if robots_txt_content is not None:
            self.set_rules(domain, robots_txt_content)

        parser = self._parsers.get(domain)
        if parser is None:
            return True

        return bool(parser.can_fetch(ua, url))


robots_checker = RobotsChecker()

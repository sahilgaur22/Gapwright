import logging

from app.core.config import settings
from app.services.sources.base import BaseJobSource

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registry managing job source connectors, configured filters, and priorities."""

    def __init__(self) -> None:
        self._source_classes: dict[str, type[BaseJobSource]] = {}
        self._instances: dict[str, BaseJobSource] = {}

    def register(self, connector_cls: type[BaseJobSource]) -> type[BaseJobSource]:
        """Register a job source connector class."""
        instance = connector_cls()
        name = instance.name.lower().strip()
        self._source_classes[name] = connector_cls
        self._instances[name] = instance
        logger.debug(
            f"Registered job source: {name} (Priority {instance.priority})"
        )
        return connector_cls

    def get_source(self, name: str) -> BaseJobSource | None:
        """Return the connector instance for a given source name."""
        return self._instances.get(name.lower().strip())

    def get_configured_source_names(self) -> list[str]:
        """Parse ENABLED_SOURCES from settings into a list of lowercase names."""
        raw = settings.ENABLED_SOURCES or ""
        return [s.strip().lower() for s in raw.split(",") if s.strip()]

    def is_source_enabled(self, name: str) -> bool:
        """Check whether a specific source is enabled in config."""
        return name.lower().strip() in self.get_configured_source_names()

    def get_enabled_sources(self) -> list[BaseJobSource]:
        """Return active connectors filtered by config and sorted by priority.

        P1 primary sources (priority 1) appear first, followed by P2, P3, and fixtures.
        """
        enabled_names = set(self.get_configured_source_names())
        active = [
            inst for name, inst in self._instances.items()
            if name in enabled_names
        ]
        active.sort(key=lambda s: (s.priority, s.name))
        return active

    def clear(self) -> None:
        """Clear registered sources (useful for test resets)."""
        self._source_classes.clear()
        self._instances.clear()


source_registry = SourceRegistry()

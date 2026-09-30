from app.services.sources.adzuna import AdzunaSource
from app.services.sources.arbeitnow import ArbeitnowSource
from app.services.sources.base import BaseJobSource
from app.services.sources.budget import (
    BudgetExhaustedError,
    check_budget,
    get_daily_usage,
    get_remaining_budget,
    record_usage,
)
from app.services.sources.cache import ResponseCache, response_cache
from app.services.sources.fixture import FixtureSource
from app.services.sources.hn_hiring import HNHiringSource
from app.services.sources.jooble import JoobleSource
from app.services.sources.limiter import DomainRateLimiter, TokenBucket, rate_limiter
from app.services.sources.models import RawJob
from app.services.sources.registry import SourceRegistry, source_registry
from app.services.sources.remoteok import RemoteOKSource
from app.services.sources.remotive import RemotiveSource
from app.services.sources.robots import RobotsChecker, robots_checker
from app.services.sources.seed import INITIAL_JOB_SOURCES, seed_job_sources
from app.services.sources.wwr_rss import WeWorkRemotelyRSSSource

# Register available connectors
source_registry.register(AdzunaSource)
source_registry.register(JoobleSource)
source_registry.register(RemotiveSource)
source_registry.register(RemoteOKSource)
source_registry.register(WeWorkRemotelyRSSSource)
source_registry.register(ArbeitnowSource)
source_registry.register(HNHiringSource)
source_registry.register(FixtureSource)

__all__ = [
    "AdzunaSource",
    "ArbeitnowSource",
    "BaseJobSource",
    "BudgetExhaustedError",
    "DomainRateLimiter",
    "FixtureSource",
    "HNHiringSource",
    "INITIAL_JOB_SOURCES",
    "JoobleSource",
    "RawJob",
    "RemoteOKSource",
    "RemotiveSource",
    "ResponseCache",
    "RobotsChecker",
    "SourceRegistry",
    "TokenBucket",
    "WeWorkRemotelyRSSSource",
    "check_budget",
    "get_daily_usage",
    "get_remaining_budget",
    "rate_limiter",
    "record_usage",
    "response_cache",
    "robots_checker",
    "seed_job_sources",
    "source_registry",
]

import time
from collections.abc import AsyncGenerator
from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.models.job import JobSource
from app.services.sources.base import BaseJobSource
from app.services.sources.budget import (
    check_budget,
    get_daily_usage,
    get_remaining_budget,
    record_usage,
)
from app.services.sources.cache import ResponseCache
from app.services.sources.limiter import DomainRateLimiter, TokenBucket
from app.services.sources.models import RawJob
from app.services.sources.registry import SourceRegistry
from app.services.sources.robots import RobotsChecker
from app.services.sources.seed import seed_job_sources


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


# --- Budget Tests ---

@pytest.mark.asyncio
async def test_api_usage_budget_flow(test_session: AsyncSession) -> None:
    source_name = "adzuna"
    limit = 30
    today = date.today()

    # Initial usage should be 0
    assert await get_daily_usage(test_session, source_name, today) == 0
    assert await get_remaining_budget(test_session, source_name, limit, today) == 30
    assert await check_budget(test_session, source_name, limit, 1, today) is True

    # Record 10 calls
    used = await record_usage(test_session, source_name, 10, today)
    assert used == 10
    assert await get_daily_usage(test_session, source_name, today) == 10
    assert await get_remaining_budget(test_session, source_name, limit, today) == 20
    assert await check_budget(test_session, source_name, limit, 20, today) is True
    assert await check_budget(test_session, source_name, limit, 21, today) is False

    # Record 20 more calls -> reaches exactly limit
    used = await record_usage(test_session, source_name, 20, today)
    assert used == 30
    assert await get_remaining_budget(test_session, source_name, limit, today) == 0
    assert await check_budget(test_session, source_name, limit, 1, today) is False


# --- Rate Limiter Tests ---

@pytest.mark.asyncio
async def test_token_bucket_and_rate_limiter() -> None:
    # Direct TokenBucket test
    bucket = TokenBucket(capacity=2.0, refill_rate=10.0)
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is True
    assert bucket.consume(1.0) is False

    # Limiter with politeness delay
    limiter = DomainRateLimiter(default_capacity=5.0, default_refill_rate=5.0)
    limiter.set_rule(
        "test.domain", capacity=2.0, refill_rate=10.0, min_delay_seconds=0.1
    )

    t0 = time.monotonic()
    assert await limiter.acquire("test.domain", tokens=1.0) is True
    assert await limiter.acquire("test.domain", tokens=1.0) is True
    elapsed = time.monotonic() - t0
    # Must have waited at least 0.1s for politeness delay
    assert elapsed >= 0.09

    # Timeout test when bucket is exhausted
    limiter.set_rule("busy.domain", capacity=0.0, refill_rate=0.0)
    res = await limiter.acquire("busy.domain", tokens=1.0, timeout=0.1)
    assert res is False


# --- Cache Tests ---

def test_response_cache() -> None:
    cache = ResponseCache(default_ttl_seconds=1)
    cache.set("key1", {"jobs": ["jobA", "jobB"]})
    assert cache.get("key1") == {"jobs": ["jobA", "jobB"]}
    assert cache.get("nonexistent") is None

    # Deletion
    cache.delete("key1")
    assert cache.get("key1") is None

    # Expiration
    cache.set("short_key", "value", ttl_seconds=0)
    time.sleep(0.01)
    assert cache.get("short_key") is None


# --- Robots Tests ---

def test_robots_txt_checker() -> None:
    checker = RobotsChecker()
    robots_content = (
        "User-agent: GapwrightBot\n"
        "Disallow: /admin/\n"
        "Disallow: /private/\n"
        "Allow: /jobs/\n"
    )

    base = "https://example.com"
    checker.set_rules(base, robots_content)

    assert checker.is_allowed(
        "https://example.com/jobs/123", user_agent="GapwrightBot"
    ) is True
    assert checker.is_allowed(
        "https://example.com/admin/login", user_agent="GapwrightBot"
    ) is False
    assert checker.is_allowed(
        "https://example.com/private/data", user_agent="GapwrightBot"
    ) is False

    # Different user-agent should not be affected by GapwrightBot rules
    assert checker.is_allowed(
        "https://example.com/admin/login", user_agent="OtherBot"
    ) is True

    # Unconfigured domain defaults to allowed
    assert checker.is_allowed("https://otherdomain.org/jobs") is True


# --- Registry Tests ---

class DummyP1Source(BaseJobSource):
    @property
    def name(self) -> str:
        return "dummy_p1"

    @property
    def priority(self) -> int:
        return 1

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[RawJob]:
        return []


class DummyP2Source(BaseJobSource):
    @property
    def name(self) -> str:
        return "dummy_p2"

    @property
    def priority(self) -> int:
        return 2

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[RawJob]:
        return []


def test_source_registry_filtering_and_priority() -> None:
    reg = SourceRegistry()
    reg.register(DummyP2Source)
    reg.register(DummyP1Source)

    assert reg.get_source("dummy_p1") is not None
    assert reg.get_source("dummy_p2") is not None
    assert reg.get_source("unknown") is None

    # Test sorting: P1 before P2 when both are enabled
    prev = settings.ENABLED_SOURCES
    try:
        settings.ENABLED_SOURCES = "dummy_p2,dummy_p1"
        enabled = reg.get_enabled_sources()
        assert len(enabled) == 2
        assert enabled[0].name == "dummy_p1"
        assert enabled[1].name == "dummy_p2"

        # Test filtering: only dummy_p1 enabled
        settings.ENABLED_SOURCES = "dummy_p1"
        enabled_filtered = reg.get_enabled_sources()
        assert len(enabled_filtered) == 1
        assert enabled_filtered[0].name == "dummy_p1"
    finally:
        settings.ENABLED_SOURCES = prev


# --- Seed Job Sources Tests ---

@pytest.mark.asyncio
async def test_seed_job_sources(test_session: AsyncSession) -> None:
    # First seed run inserts all sources
    created = await seed_job_sources(test_session)
    assert created == 8

    # Query sources from DB
    res = await test_session.execute(select(JobSource).order_by(JobSource.priority))
    sources = list(res.scalars().all())
    source_names = [s.name for s in sources]

    assert "adzuna" in source_names
    assert "jooble" in source_names
    assert "remotive" in source_names
    assert "remoteok" in source_names
    assert "wwr_rss" in source_names
    assert "arbeitnow" in source_names
    assert "hn_hiring" in source_names
    assert "fixture" in source_names

    # Check terms for remotive
    remotive = next(s for s in sources if s.name == "remotive")
    assert remotive.may_display_listing is False
    assert remotive.priority == 2
    assert remotive.attribution_text == "Data from Remotive"

    # Second seed run is idempotent (0 added)
    created_second = await seed_job_sources(test_session)
    assert created_second == 0

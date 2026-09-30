import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from app.services.sources.registry import source_registry
from app.services.sources.remoteok import RemoteOKSource
from app.services.sources.remotive import RemotiveSource
from app.services.sources.wwr_rss import WeWorkRemotelyRSSSource

FIXTURES_DIR = Path(__file__).parent / "fixtures"
REMOTIVE_FIXTURE_PATH = FIXTURES_DIR / "remotive_jobs_response.json"
REMOTEOK_FIXTURE_PATH = FIXTURES_DIR / "remoteok_jobs_response.json"
WWR_FIXTURE_PATH = FIXTURES_DIR / "wwr_feed_response.xml"


@pytest.fixture
def remotive_fixture_data() -> dict:
    return json.loads(REMOTIVE_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def remoteok_fixture_data() -> list:
    return json.loads(REMOTEOK_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def wwr_fixture_xml() -> str:
    return WWR_FIXTURE_PATH.read_text(encoding="utf-8")


# ============================================================================
# Remotive Tests
# ============================================================================


@pytest.mark.asyncio
@respx.mock
async def test_remotive_search_success_with_recorded_fixture(
    remotive_fixture_data: dict,
) -> None:
    source = RemotiveSource()

    route = respx.get("https://remotive.com/api/remote-jobs").respond(
        status_code=200,
        json=remotive_fixture_data,
    )

    jobs = await source.search(role="Python", limit=10)

    assert route.called
    assert len(jobs) == 2

    job = jobs[0]
    assert job.source == "remotive"
    assert job.external_id == "1928371"
    assert job.title == "Senior Python Backend Engineer"
    assert job.company == "GitLab"
    assert job.location == "Worldwide"
    assert "async programming" in job.description
    assert "<p>" not in job.description  # HTML tags cleaned
    assert (
        job.url
        == "https://remotive.com/remote-jobs/software-dev/senior-python-dev-1928371"
    )
    assert job.attribution_text == "Data from Remotive"
    assert job.attribution_url == "https://remotive.com"
    # Terms restriction: Remotive data is for internal statistics only
    assert job.may_display_listing is False
    assert job.posted_at == datetime(2026, 9, 28, 9, 30, tzinfo=UTC)

    # Check query params
    request = route.calls[0].request
    assert request.url.params["search"] == "Python"
    assert request.url.params["limit"] == "10"


@pytest.mark.asyncio
@respx.mock
async def test_remotive_search_filters_by_since_cutoff(
    remotive_fixture_data: dict,
) -> None:
    source = RemotiveSource()

    respx.get("https://remotive.com/api/remote-jobs").respond(
        status_code=200,
        json=remotive_fixture_data,
    )

    # Cutoff after 2026-09-28 00:00:00 UTC - only job 1928371 was posted on Sep 28
    since = datetime(2026, 9, 28, 0, 0, tzinfo=UTC)
    jobs = await source.search(role="Python", since=since, limit=10)
    assert len(jobs) == 1
    assert jobs[0].external_id == "1928371"


@pytest.mark.asyncio
@respx.mock
async def test_remotive_search_network_error_returns_empty() -> None:
    source = RemotiveSource()

    respx.get("https://remotive.com/api/remote-jobs").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    jobs = await source.search(role="Engineer", limit=10)
    assert jobs == []


@pytest.mark.asyncio
@respx.mock
async def test_remotive_search_http_500_returns_empty() -> None:
    source = RemotiveSource()

    respx.get("https://remotive.com/api/remote-jobs").respond(status_code=500)

    jobs = await source.search(role="Engineer", limit=10)
    assert jobs == []


# ============================================================================
# RemoteOK Tests
# ============================================================================


@pytest.mark.asyncio
@respx.mock
async def test_remoteok_search_success_with_recorded_fixture(
    remoteok_fixture_data: list,
) -> None:
    source = RemoteOKSource()

    route = respx.get("https://remoteok.com/api").respond(
        status_code=200,
        json=remoteok_fixture_data,
    )

    jobs = await source.search(role="Data Engineer", limit=10)

    assert route.called
    assert len(jobs) == 1

    job = jobs[0]
    assert job.source == "remoteok"
    assert job.external_id == "908124"
    assert job.title == "Staff Data Engineer"
    assert job.company == "Automattic"
    assert job.location == "Worldwide"
    assert "petabyte-scale" in job.description
    assert "<p>" not in job.description  # HTML tags cleaned
    assert job.url == "https://remoteok.com/remote-jobs/908124-staff-data-engineer"
    assert job.attribution_text == "Jobs by RemoteOK"
    assert job.attribution_url == "https://remoteok.com"
    assert job.may_display_listing is True
    assert job.posted_at == datetime(2026, 9, 28, 10, 40, tzinfo=UTC)


@pytest.mark.asyncio
@respx.mock
async def test_remoteok_skips_legal_preamble_element(
    remoteok_fixture_data: list,
) -> None:
    # Ensure the first element in fixture is indeed legal/terms
    assert "legal" in remoteok_fixture_data[0]

    source = RemoteOKSource()
    respx.get("https://remoteok.com/api").respond(
        status_code=200,
        json=remoteok_fixture_data,
    )

    # Empty role returns all valid job objects, skipping legal notice
    jobs = await source.search(role="", limit=10)
    assert len(jobs) == 2
    external_ids = {j.external_id for j in jobs}
    assert external_ids == {"908124", "908125"}


def test_remoteok_has_politeness_delay() -> None:
    source = RemoteOKSource()
    assert source.min_delay_seconds >= 0.5


@pytest.mark.asyncio
@respx.mock
async def test_remoteok_search_network_error_returns_empty() -> None:
    source = RemoteOKSource()

    respx.get("https://remoteok.com/api").mock(
        side_effect=httpx.ConnectError("Network timeout")
    )

    jobs = await source.search(role="Python Developer", limit=10)
    assert jobs == []


# ============================================================================
# We Work Remotely (WWR) RSS Tests
# ============================================================================


@pytest.mark.asyncio
@respx.mock
async def test_wwr_rss_search_success_with_recorded_fixture(
    wwr_fixture_xml: str,
) -> None:
    source = WeWorkRemotelyRSSSource()

    route = respx.get(
        "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    ).respond(
        status_code=200,
        text=wwr_fixture_xml,
        headers={"Content-Type": "application/rss+xml"},
    )

    jobs = await source.search(role="Platform Engineer", limit=10)

    assert route.called
    assert len(jobs) == 1

    job = jobs[0]
    assert job.source == "wwr_rss"
    assert job.external_id == "wwr-job-101"
    # Extracted company and role title from "DuckDuckGo: Senior Platform Engineer"
    assert job.company == "DuckDuckGo"
    assert job.title == "Senior Platform Engineer"
    assert job.location == "Remote"
    assert "Linux networking" in job.description
    assert "<p>" not in job.description  # HTML tags cleaned
    assert job.attribution_text == "Jobs via We Work Remotely"
    assert job.attribution_url == "https://weworkremotely.com"
    assert job.may_display_listing is True
    assert job.posted_at == datetime(2026, 9, 28, 10, 15, tzinfo=UTC)


@pytest.mark.asyncio
@respx.mock
async def test_wwr_rss_filters_by_query_terms(
    wwr_fixture_xml: str,
) -> None:
    source = WeWorkRemotelyRSSSource()

    respx.get(
        "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    ).respond(
        status_code=200,
        text=wwr_fixture_xml,
        headers={"Content-Type": "application/rss+xml"},
    )

    jobs = await source.search(role="Security", limit=10)
    assert len(jobs) == 1
    assert jobs[0].company == "Stripe"
    assert jobs[0].title == "Infrastructure Security Specialist"


@pytest.mark.asyncio
@respx.mock
async def test_wwr_rss_network_error_returns_empty() -> None:
    source = WeWorkRemotelyRSSSource()

    respx.get("https://weworkremotely.com/categories/remote-programming-jobs.rss").mock(
        side_effect=httpx.ConnectError("RSS connection failed")
    )

    jobs = await source.search(role="Engineer", limit=10)
    assert jobs == []


# ============================================================================
# Registry Verification
# ============================================================================


def test_registry_contains_all_five_connectors() -> None:
    assert source_registry.get_source("adzuna") is not None
    assert source_registry.get_source("jooble") is not None
    assert source_registry.get_source("remotive") is not None
    assert source_registry.get_source("remoteok") is not None
    assert source_registry.get_source("wwr_rss") is not None

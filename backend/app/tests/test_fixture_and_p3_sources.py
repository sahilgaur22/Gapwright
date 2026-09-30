import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from app.services.sources.arbeitnow import ArbeitnowSource
from app.services.sources.fixture import FixtureSource
from app.services.sources.hn_hiring import HNHiringSource, _extract_hn_job_metadata
from app.services.sources.registry import source_registry
from app.services.sources.seed import INITIAL_JOB_SOURCES

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ARBEITNOW_FIXTURE_PATH = FIXTURES_DIR / "arbeitnow_jobs_response.json"
HN_STORIES_FIXTURE_PATH = FIXTURES_DIR / "hn_stories_response.json"
HN_COMMENTS_FIXTURE_PATH = FIXTURES_DIR / "hn_comments_response.json"


@pytest.fixture
def arbeitnow_fixture_data() -> dict:
    return json.loads(ARBEITNOW_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def hn_stories_fixture_data() -> dict:
    return json.loads(HN_STORIES_FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def hn_comments_fixture_data() -> dict:
    return json.loads(HN_COMMENTS_FIXTURE_PATH.read_text(encoding="utf-8"))


# ============================================================================
# FixtureSource Tests (Offline, Curated Indian Tech Jobs)
# ============================================================================


@pytest.mark.asyncio
async def test_fixture_source_loads_curated_indian_jobs() -> None:
    source = FixtureSource()
    jobs = await source.search(role="Data Scientist", location="Bangalore", limit=10)

    assert len(jobs) >= 1
    job = jobs[0]
    assert job.source == "fixture"
    assert "Data Scientist" in job.title
    assert job.location is not None and "Bangalore" in job.location
    assert job.company == "Swiggy"
    assert "PyTorch" in job.description
    assert job.may_display_listing is True
    assert job.attribution_text == "Curated sample dataset"
    assert job.posted_at is not None


@pytest.mark.asyncio
async def test_fixture_source_filters_by_role_and_location() -> None:
    source = FixtureSource()

    # Query for SRE in Bangalore
    sre_jobs = await source.search(role="Site Reliability", location="Bangalore")
    assert len(sre_jobs) >= 1
    assert any("Zerodha" in (j.company or "") for j in sre_jobs)

    # Query for DevOps in Hyderabad
    devops_jobs = await source.search(role="DevOps", location="Hyderabad")
    assert len(devops_jobs) >= 1
    assert any("ServiceNow" in (j.company or "") for j in devops_jobs)


@pytest.mark.asyncio
async def test_fixture_source_location_india_matches_all_hubs() -> None:
    source = FixtureSource()
    all_india_jobs = await source.search(role="", location="India", limit=50)
    assert len(all_india_jobs) >= 10


@pytest.mark.asyncio
async def test_fixture_source_respects_since_cutoff() -> None:
    source = FixtureSource()
    cutoff = datetime(2026, 9, 29, 0, 0, tzinfo=UTC)
    recent_jobs = await source.search(role="", since=cutoff, limit=50)

    for job in recent_jobs:
        assert job.posted_at is not None
        assert job.posted_at >= cutoff


@pytest.mark.asyncio
async def test_fixture_source_handles_missing_file_gracefully(tmp_path: Path) -> None:
    missing_path = tmp_path / "does_not_exist.json"
    source = FixtureSource(data_path=missing_path)
    jobs = await source.search(role="Developer")
    assert jobs == []


# ============================================================================
# Arbeitnow Tests (EU & Remote, P3)
# ============================================================================


@pytest.mark.asyncio
@respx.mock
async def test_arbeitnow_search_success_with_recorded_fixture(
    arbeitnow_fixture_data: dict,
) -> None:
    source = ArbeitnowSource()

    route = respx.get("https://www.arbeitnow.com/api/job-board-api").respond(
        status_code=200,
        json=arbeitnow_fixture_data,
    )

    jobs = await source.search(role="Python", location="Berlin", limit=10)

    assert route.called
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "arbeitnow"
    assert job.external_id == "senior-python-backend-engineer-berlin-1001"
    assert job.title == "Senior Python Backend Engineer"
    assert job.company == "Delivery Hero"
    assert "FastAPI" in job.description
    assert "<p>" not in job.description  # HTML tags cleaned
    assert job.location == "Berlin, Germany"
    assert job.attribution_text == "Jobs by Arbeitnow"
    assert job.attribution_url == "https://www.arbeitnow.com"
    assert job.may_display_listing is True


@pytest.mark.asyncio
@respx.mock
async def test_arbeitnow_search_network_error_returns_empty() -> None:
    source = ArbeitnowSource()

    respx.get("https://www.arbeitnow.com/api/job-board-api").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    jobs = await source.search(role="Python", limit=10)
    assert jobs == []


# ============================================================================
# HN Hiring Tests (Algolia API, P3)
# ============================================================================


def test_extract_hn_job_metadata() -> None:
    text = (
        "Stripe | Infrastructure Engineer | San Francisco, CA | Full-Time\n"
        "We build payments."
    )
    company, title, location = _extract_hn_job_metadata(text)
    assert company == "Stripe"
    assert title == "Infrastructure Engineer"
    assert location == "San Francisco, CA"


@pytest.mark.asyncio
@respx.mock
async def test_hn_hiring_search_success_with_recorded_fixture(
    hn_stories_fixture_data: dict,
    hn_comments_fixture_data: dict,
) -> None:
    source = HNHiringSource()

    # Route 1: find story
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(200, json=hn_stories_fixture_data)
    )

    # Route 2: fetch comments for story 41415161
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(200, json=hn_comments_fixture_data)
    )

    # We use a custom router to distinguish calls by params
    respx.clear()
    story_route = respx.get(
        "https://hn.algolia.com/api/v1/search_by_date",
        params__contains={"tags": "story,author_whoishiring"},
    ).respond(status_code=200, json=hn_stories_fixture_data)

    comment_route = respx.get(
        "https://hn.algolia.com/api/v1/search_by_date",
        params__contains={"tags": "comment,story_41415161"},
    ).respond(status_code=200, json=hn_comments_fixture_data)

    jobs = await source.search(role="Infrastructure", limit=10)

    assert story_route.called
    assert comment_route.called
    assert len(jobs) == 1

    job = jobs[0]
    assert job.source == "hn_hiring"
    assert job.external_id == "41415999"
    assert job.company == "Stripe"
    assert job.title == "Infrastructure Engineer"
    assert job.location == "San Francisco, CA"
    assert "Kubernetes" in job.description
    assert "<p>" not in job.description  # HTML tags cleaned
    assert job.url == "https://news.ycombinator.com/item?id=41415999"
    assert job.attribution_text == "Hacker News Who is Hiring"
    assert job.may_display_listing is True


@pytest.mark.asyncio
@respx.mock
async def test_hn_hiring_no_story_returns_empty() -> None:
    source = HNHiringSource()

    respx.get("https://hn.algolia.com/api/v1/search_by_date").respond(
        status_code=200,
        json={"hits": []},
    )

    jobs = await source.search(role="Developer", limit=10)
    assert jobs == []


# ============================================================================
# Registry and Defaults Verification
# ============================================================================


def test_registry_contains_all_sources() -> None:
    assert source_registry.get_source("adzuna") is not None
    assert source_registry.get_source("jooble") is not None
    assert source_registry.get_source("remotive") is not None
    assert source_registry.get_source("remoteok") is not None
    assert source_registry.get_source("wwr_rss") is not None
    assert source_registry.get_source("arbeitnow") is not None
    assert source_registry.get_source("hn_hiring") is not None
    assert source_registry.get_source("fixture") is not None


def test_p3_sources_are_disabled_by_default() -> None:
    initial_map = {str(item["name"]): item for item in INITIAL_JOB_SOURCES}
    assert initial_map["arbeitnow"]["enabled"] is False
    assert initial_map["hn_hiring"]["enabled"] is False
    assert initial_map["fixture"]["enabled"] is True

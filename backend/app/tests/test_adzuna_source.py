import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from app.services.sources.adzuna import AdzunaSource

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "adzuna_search_response.json"


@pytest.fixture
def adzuna_fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_search_success_with_recorded_fixture(
    adzuna_fixture_data: dict,
) -> None:
    source = AdzunaSource(app_id="test_id", app_key="test_key", country="in")

    route = respx.get("https://api.adzuna.com/v1/api/jobs/in/search/1").respond(
        status_code=200,
        json=adzuna_fixture_data,
    )

    jobs = await source.search(role="Data Scientist", location="Bangalore", limit=10)

    assert route.called
    assert len(jobs) == 2

    job1 = jobs[0]
    assert job1.source == "adzuna"
    assert job1.external_id == "4810291011"
    assert job1.title == "Lead Data Scientist"
    assert job1.company == "Fractal Analytics"
    assert job1.location == "Bangalore, Karnataka"
    assert "Python" in job1.description
    assert job1.description_is_truncated is True
    assert job1.url == "https://www.adzuna.in/land/ad/4810291011?se=sample"
    assert job1.attribution_text == "Powered by Adzuna"
    assert job1.attribution_url == "https://www.adzuna.com"
    assert job1.may_display_listing is True
    assert job1.posted_at == datetime(2026, 9, 28, 8, 30, tzinfo=UTC)

    # Verify query params passed to Adzuna
    request = route.calls[0].request
    assert request.url.params["app_id"] == "test_id"
    assert request.url.params["app_key"] == "test_key"
    assert request.url.params["what"] == "Data Scientist"
    assert request.url.params["where"] == "Bangalore"
    assert request.url.params["sort_by"] == "date"


@pytest.mark.asyncio
async def test_adzuna_missing_credentials_returns_empty() -> None:
    source = AdzunaSource(app_id=None, app_key=None)
    jobs = await source.search(role="Backend Engineer", location="Bangalore")
    assert jobs == []


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_pagination_respects_limit() -> None:
    source = AdzunaSource(
        app_id="test_id", app_key="test_key", country="in", page_size=2
    )

    page1_payload = {
        "results": [
            {
                "id": f"p1_{i}",
                "title": f"DevOps Engineer {i}",
                "company": {"display_name": "CloudCorp"},
                "location": {"display_name": "Bangalore"},
                "description": "Docker, Kubernetes, Terraform",
                "redirect_url": f"https://adzuna.in/job/p1_{i}",
                "created": "2026-09-28T10:00:00Z",
            }
            for i in range(2)
        ]
    }
    page2_payload = {
        "results": [
            {
                "id": f"p2_{i}",
                "title": f"DevOps Engineer Page 2 {i}",
                "company": {"display_name": "CloudCorp"},
                "location": {"display_name": "Bangalore"},
                "description": "Docker, Kubernetes, Terraform",
                "redirect_url": f"https://adzuna.in/job/p2_{i}",
                "created": "2026-09-27T10:00:00Z",
            }
            for i in range(2)
        ]
    }

    r1 = respx.get("https://api.adzuna.com/v1/api/jobs/in/search/1").respond(
        status_code=200, json=page1_payload
    )
    r2 = respx.get("https://api.adzuna.com/v1/api/jobs/in/search/2").respond(
        status_code=200, json=page2_payload
    )

    # Request limit=3: Should fetch 2 from page 1, 1 from page 2
    jobs = await source.search(role="DevOps", location="Bangalore", limit=3)

    assert r1.called
    assert r2.called
    assert len(jobs) == 3
    assert jobs[0].external_id == "p1_0"
    assert jobs[1].external_id == "p1_1"
    assert jobs[2].external_id == "p2_0"


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_retry_on_transient_error(adzuna_fixture_data: dict) -> None:
    source = AdzunaSource(
        app_id="test_id",
        app_key="test_key",
        country="in",
        max_retries=3,
        backoff_factor=0.01,
    )

    # First call returns 429, second call returns 200
    route = respx.get("https://api.adzuna.com/v1/api/jobs/in/search/1")
    route.side_effect = [
        httpx.Response(status_code=429, json={"error": "Rate limit exceeded"}),
        httpx.Response(status_code=200, json=adzuna_fixture_data),
    ]

    jobs = await source.search(role="Data Scientist", limit=5)
    assert len(jobs) == 2
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_adzuna_failure_returns_empty() -> None:
    source = AdzunaSource(
        app_id="test_id",
        app_key="test_key",
        country="in",
        max_retries=2,
        backoff_factor=0.01,
    )

    route = respx.get("https://api.adzuna.com/v1/api/jobs/in/search/1").respond(
        status_code=500, json={"error": "Internal server error"}
    )

    jobs = await source.search(role="Data Scientist", limit=5)
    assert jobs == []
    assert route.call_count == 2

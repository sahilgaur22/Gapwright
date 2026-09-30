import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from app.services.sources.jooble import JoobleSource

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "jooble_search_response.json"


@pytest.fixture
def jooble_fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.asyncio
@respx.mock
async def test_jooble_search_success_with_recorded_fixture(
    jooble_fixture_data: dict,
) -> None:
    source = JoobleSource(api_key="test_secret_key")

    route = respx.post("https://jooble.org/api/test_secret_key").respond(
        status_code=200,
        json=jooble_fixture_data,
    )

    jobs = await source.search(role="Data Scientist", location="Bangalore", limit=10)

    assert route.called
    assert len(jobs) == 2

    job1 = jobs[0]
    assert job1.source == "jooble"
    assert job1.external_id == "8930124"
    assert job1.title == "Senior Data Scientist"
    assert job1.company == "Swiggy"
    assert job1.location == "Bangalore, Karnataka, India"
    assert "Python" in job1.description
    assert job1.description_is_truncated is True
    assert job1.url == "https://jooble.org/desc/8930124?ckey=test"
    assert job1.attribution_text == "Jobs via Jooble"
    assert job1.attribution_url == "https://jooble.org"
    assert job1.may_display_listing is True
    assert job1.posted_at == datetime(2026, 9, 29, 11, 45, tzinfo=UTC)

    # Verify JSON body passed to Jooble API
    req_body = json.loads(route.calls[0].request.content)
    assert req_body["keywords"] == "Data Scientist"
    assert req_body["location"] == "Bangalore"
    assert req_body["page"] == 1
    assert req_body["resultonpage"] == 20


@pytest.mark.asyncio
async def test_jooble_missing_key_disables_gracefully() -> None:
    # Key not yet issued
    source = JoobleSource(api_key=None)
    jobs = await source.search(role="Backend Engineer", location="Bangalore")
    assert jobs == []

    empty_key_source = JoobleSource(api_key="")
    jobs_empty = await empty_key_source.search(role="Data Scientist")
    assert jobs_empty == []


@pytest.mark.asyncio
@respx.mock
async def test_jooble_pagination_respects_limit() -> None:
    source = JoobleSource(api_key="key_123", page_size=2)

    page1_payload = {
        "totalCount": 4,
        "jobs": [
            {
                "id": f"jb_1_{i}",
                "title": f"ML Engineer {i}",
                "company": "DeepTech",
                "location": "Bangalore",
                "snippet": "PyTorch, CUDA, Distributed Training",
                "link": f"https://jooble.org/desc/{i}",
                "updated": "2026-09-29T10:00:00Z",
            }
            for i in range(2)
        ],
    }
    page2_payload = {
        "totalCount": 4,
        "jobs": [
            {
                "id": f"jb_2_{i}",
                "title": f"ML Engineer Page 2 {i}",
                "company": "DeepTech",
                "location": "Bangalore",
                "snippet": "PyTorch, CUDA, Distributed Training",
                "link": f"https://jooble.org/desc/p2_{i}",
                "updated": "2026-09-28T10:00:00Z",
            }
            for i in range(2)
        ],
    }

    route = respx.post("https://jooble.org/api/key_123")
    route.side_effect = [
        httpx.Response(status_code=200, json=page1_payload),
        httpx.Response(status_code=200, json=page2_payload),
    ]

    jobs = await source.search(role="ML Engineer", location="Bangalore", limit=3)

    assert route.call_count == 2
    assert len(jobs) == 3
    assert jobs[0].external_id == "jb_1_0"
    assert jobs[1].external_id == "jb_1_1"
    assert jobs[2].external_id == "jb_2_0"


@pytest.mark.asyncio
@respx.mock
async def test_jooble_retry_on_transient_error(jooble_fixture_data: dict) -> None:
    source = JoobleSource(
        api_key="retry_key",
        max_retries=3,
        backoff_factor=0.01,
    )

    route = respx.post("https://jooble.org/api/retry_key")
    route.side_effect = [
        httpx.Response(status_code=503, json={"error": "Service unavailable"}),
        httpx.Response(status_code=200, json=jooble_fixture_data),
    ]

    jobs = await source.search(role="Data Scientist", limit=5)
    assert len(jobs) == 2
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_jooble_failure_returns_empty() -> None:
    source = JoobleSource(
        api_key="fail_key",
        max_retries=2,
        backoff_factor=0.01,
    )

    route = respx.post("https://jooble.org/api/fail_key").respond(
        status_code=500, json={"error": "Internal server error"}
    )

    jobs = await source.search(role="Data Scientist", limit=5)
    assert jobs == []
    assert route.call_count == 2

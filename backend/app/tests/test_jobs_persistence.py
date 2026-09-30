from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.job import JobPosting, JobSkill
from app.db.session import get_db
from app.main import app
from app.services.crawl.state import get_crawl_state, update_crawl_state
from app.services.jobs.persistence import persist_raw_jobs
from app.services.llm.base import LLMProvider
from app.services.sources.models import RawJob
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
        # Seed initial job sources into DB
        await seed_job_sources(session)
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm_provider() -> AsyncMock:
    provider = AsyncMock(spec=LLMProvider)
    extraction_payload = {
        "skills": [
            {
                "name": "Python",
                "category": "Programming Languages",
                "confidence": 0.95,
                "evidence": "developing microservices using Python",
            },
            {
                "name": "FastAPI",
                "category": "Frameworks",
                "confidence": 0.90,
                "evidence": "microservices using FastAPI",
            },
        ]
    }
    provider.extract_json.return_value = extraction_payload
    return provider


# ============================================================================
# Persistence, Deduplication & Skill Extraction Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persist_raw_jobs_creates_postings_and_extracts_skills(
    test_session: AsyncSession,
    mock_llm_provider: AsyncMock,
) -> None:
    raw_jobs = [
        RawJob(
            source="fixture",
            external_id="job-101",
            title="Senior Python Backend Developer",
            company="Swiggy",
            location="Bangalore",
            description=(
                "Developing high throughput microservices using Python and FastAPI."
            ),
            posted_at=datetime(2026, 9, 28, 10, 0, tzinfo=UTC),
        )
    ]

    res = await persist_raw_jobs(
        test_session,
        raw_jobs,
        extract_skills=True,
        llm_provider=mock_llm_provider,
    )

    assert res.created_count == 1
    assert res.updated_count == 0
    assert res.duplicate_count == 0
    assert res.extracted_skills_count >= 2
    assert mock_llm_provider.extract_json.call_count == 1

    # Verify job in DB
    jobs_res = await test_session.execute(select(JobPosting))
    jobs = list(jobs_res.scalars().all())
    assert len(jobs) == 1
    assert jobs[0].external_id == "job-101"

    # Verify skills linked in DB
    skills_res = await test_session.execute(select(JobSkill))
    skills = list(skills_res.scalars().all())
    assert len(skills) >= 2


@pytest.mark.asyncio
async def test_rerun_crawl_creates_no_duplicates_and_no_repeat_llm_calls(
    test_session: AsyncSession,
    mock_llm_provider: AsyncMock,
) -> None:
    raw_job = RawJob(
        source="fixture",
        external_id="job-dedupe-1",
        title="Lead Data Scientist",
        company="Razorpay",
        location="Bangalore",
        description="Machine learning engineering with PyTorch and Python.",
        posted_at=datetime(2026, 9, 28, 10, 0, tzinfo=UTC),
    )

    # Initial crawl run
    res1 = await persist_raw_jobs(
        test_session,
        [raw_job],
        extract_skills=True,
        llm_provider=mock_llm_provider,
    )
    assert res1.created_count == 1
    assert mock_llm_provider.extract_json.call_count == 1

    # Reset mock call counter
    mock_llm_provider.extract_json.reset_mock()

    # Re-run identical crawl
    res2 = await persist_raw_jobs(
        test_session,
        [raw_job],
        extract_skills=True,
        llm_provider=mock_llm_provider,
    )

    # Key assertions: No duplicate row created, NO repeat LLM calls
    assert res2.created_count == 0
    assert res2.updated_count == 1
    assert res2.skipped_llm_count == 1
    assert mock_llm_provider.extract_json.call_count == 0

    # DB still contains exactly 1 row
    jobs_res = await test_session.execute(select(JobPosting))
    all_jobs = list(jobs_res.scalars().all())
    assert len(all_jobs) == 1


@pytest.mark.asyncio
async def test_cross_source_content_deduplication_skips_llm_calls(
    test_session: AsyncSession,
    mock_llm_provider: AsyncMock,
) -> None:
    job_adzuna = RawJob(
        source="adzuna",
        external_id="adzuna-999",
        title="Site Reliability Engineer",
        company="Zerodha",
        location="Bangalore",
        description="Kubernetes, Linux, and Prometheus observability.",
        posted_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
    )
    job_remoteok = RawJob(
        source="remoteok",
        external_id="remoteok-888",
        title="Site Reliability Engineer",
        company="Zerodha",
        location="Bangalore",
        description="Kubernetes, Linux, and Prometheus observability.",
        posted_at=datetime(2026, 9, 28, 9, 30, tzinfo=UTC),
    )

    # First source stores posting and extracts skills
    res1 = await persist_raw_jobs(
        test_session,
        [job_adzuna],
        extract_skills=True,
        llm_provider=mock_llm_provider,
    )
    assert res1.created_count == 1
    assert mock_llm_provider.extract_json.call_count == 1

    # Reset mock call counter
    mock_llm_provider.extract_json.reset_mock()

    # Second source supplies identical (title + company) job
    res2 = await persist_raw_jobs(
        test_session,
        [job_remoteok],
        extract_skills=True,
        llm_provider=mock_llm_provider,
    )

    # Key assertions: Recognized as duplicate across sources, LLM skipped
    assert res2.created_count == 0
    assert res2.duplicate_count == 1
    assert res2.skipped_llm_count == 1
    assert mock_llm_provider.extract_json.call_count == 0

    jobs_res = await test_session.execute(select(JobPosting))
    all_jobs = list(jobs_res.scalars().all())
    assert len(all_jobs) == 1


# ============================================================================
# Crawl State Incremental Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_crawl_state_tracking(test_session: AsyncSession) -> None:
    # Initially no state
    initial = await get_crawl_state(
        test_session, "fixture", "Data Scientist", "Bangalore"
    )
    assert initial is None

    # First run
    t1 = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    state1 = await update_crawl_state(
        test_session,
        "fixture",
        "Data Scientist",
        "Bangalore",
        newest_posted_at=t1,
    )
    assert state1.newest_posted_at == t1
    assert state1.last_run_at is not None

    # Second run with newer timestamp
    t2 = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
    state2 = await update_crawl_state(
        test_session,
        "fixture",
        "Data Scientist",
        "Bangalore",
        newest_posted_at=t2,
    )
    assert state2.newest_posted_at == t2


# ============================================================================
# API Endpoints (GET /jobs, GET /sources) Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_jobs_api_endpoint(
    client: AsyncClient,
    test_session: AsyncSession,
    mock_llm_provider: AsyncMock,
) -> None:
    raw_job = RawJob(
        source="fixture",
        external_id="api-job-1",
        title="Full Stack Engineer",
        company="Zomato",
        location="Gurgaon",
        description="React and Python development.",
        posted_at=datetime(2026, 9, 28, 14, 0, tzinfo=UTC),
    )
    await persist_raw_jobs(
        test_session,
        [raw_job],
        extract_skills=True,
        llm_provider=mock_llm_provider,
    )

    # Test basic list
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Full Stack Engineer"
    assert "Python" in data["items"][0]["skills"]

    # Test query filter by role
    resp_role = await client.get("/api/v1/jobs?role=Full+Stack")
    assert resp_role.status_code == 200
    assert resp_role.json()["total"] == 1

    resp_nonexistent = await client.get("/api/v1/jobs?role=NonexistentRole")
    assert resp_nonexistent.status_code == 200
    assert resp_nonexistent.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_sources_api_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) >= 5

    names = {s["name"] for s in sources}
    assert "adzuna" in names
    assert "jooble" in names
    assert "remotive" in names
    assert "fixture" in names

    fixture_src = next(s for s in sources if s["name"] == "fixture")
    assert fixture_src["enabled"] is True
    assert fixture_src["priority"] == 10
    assert fixture_src["remaining_budget"] > 0

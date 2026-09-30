import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.models.job import JobPosting, JobSkill, SkillDemandDaily
from app.db.models.skill import Skill
from app.db.models.user import User
from app.db.session import get_db
from app.main import app
from app.schemas.skill import SkillExtractionItem, SkillExtractionResult
from app.services.crawl.runner import expire_stale_postings
from app.services.crawl.scheduler import start_local_scheduler, stop_local_scheduler
from app.services.jobs.demand import (
    generate_demand_daily_snapshot,
    get_top_demanded_skills,
    parse_crawl_pairs,
)
from app.services.sources.seed import seed_job_sources


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        await seed_job_sources(session)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.extract_json.return_value = SkillExtractionResult(
        skills=[
            SkillExtractionItem(
                name="Python",
                category="Programming Languages",
                evidence="Python experience",
                confidence=1.0,
            ),
            SkillExtractionItem(
                name="FastAPI",
                category="Web Frameworks",
                evidence="FastAPI required",
                confidence=0.95,
            ),
        ]
    ).model_dump()
    return llm


@pytest.mark.asyncio
async def test_parse_crawl_pairs() -> None:
    pairs = parse_crawl_pairs("Data Scientist|Bangalore; Backend Developer | Delhi ; ;")
    assert pairs == [("Data Scientist", "Bangalore"), ("Backend Developer", "Delhi")]

    empty = parse_crawl_pairs("")
    assert empty == []


@pytest.mark.asyncio
async def test_crawl_endpoint_unauthenticated(client: AsyncClient) -> None:
    # 1. No auth headers provided -> 401
    resp = await client.post("/api/v1/jobs/crawl", json={})
    assert resp.status_code == 401

    # 2. Invalid X-Crawl-Token -> 401
    resp_invalid = await client.post(
        "/api/v1/jobs/crawl",
        headers={"X-Crawl-Token": "wrong-secret-token"},
        json={},
    )
    assert resp_invalid.status_code == 401


@pytest.mark.asyncio
async def test_crawl_endpoint_authenticated_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Configure token
    monkeypatch.setattr(settings, "CRAWL_TRIGGER_TOKEN", "valid-crawl-secret-token-123")

    resp = await client.post(
        "/api/v1/jobs/crawl",
        headers={"X-Crawl-Token": "valid-crawl-secret-token-123"},
        json={"sources": ["fixture"], "extract_skills": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["sources_crawled"] >= 1


@pytest.mark.asyncio
async def test_crawl_endpoint_authenticated_admin_jwt(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    # Create admin user
    admin = User(
        email="admin-crawler@example.edu",
        password_hash=get_password_hash("SecretPass123!"),
        role="admin",
    )
    test_session.add(admin)
    await test_session.commit()
    await test_session.refresh(admin)

    token = create_access_token(subject=admin.id, role="admin")
    resp = await client.post(
        "/api/v1/jobs/crawl",
        headers={"Authorization": f"Bearer {token}"},
        json={"sources": ["fixture"], "extract_skills": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_expire_stale_postings(test_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    old_time = now - timedelta(days=60)
    recent_time = now - timedelta(days=10)

    old_job = JobPosting(
        source="fixture",
        external_id="stale-job-001",
        title="Legacy Cobol Developer",
        description="Cobol mainframe support",
        last_seen_at=old_time,
        is_expired=False,
    )
    fresh_job = JobPosting(
        source="fixture",
        external_id="fresh-job-002",
        title="Modern Python Engineer",
        description="FastAPI microservices",
        last_seen_at=recent_time,
        is_expired=False,
    )
    test_session.add_all([old_job, fresh_job])
    await test_session.commit()

    expired_count = await expire_stale_postings(test_session, days=45)
    assert expired_count == 1

    await test_session.refresh(old_job)
    await test_session.refresh(fresh_job)
    assert old_job.is_expired is True
    assert fresh_job.is_expired is False


@pytest.mark.asyncio
async def test_demand_snapshots_and_top_skills(
    client: AsyncClient,
    test_session: AsyncSession,
) -> None:
    # 1. Create canonical skills
    py_skill = Skill(canonical_name="Python", category="Programming")
    docker_skill = Skill(canonical_name="Docker", category="DevOps")
    test_session.add_all([py_skill, docker_skill])
    await test_session.flush()

    # 2. Create postings
    now = datetime.now(UTC)
    p1 = JobPosting(
        source="fixture",
        external_id="post-101",
        title="Senior Python Backend Developer",
        location="Bangalore",
        description="Python backend",
        last_seen_at=now,
        is_expired=False,
    )
    p2 = JobPosting(
        source="fixture",
        external_id="post-102",
        title="Lead Python & Cloud Architect",
        location="Bangalore",
        description="Python and Docker",
        last_seen_at=now,
        is_expired=False,
    )
    test_session.add_all([p1, p2])
    await test_session.flush()

    # Associate skills
    js1 = JobSkill(job_id=p1.id, skill_id=py_skill.id, confidence=1.0)
    js2 = JobSkill(job_id=p2.id, skill_id=py_skill.id, confidence=1.0)
    js3 = JobSkill(job_id=p2.id, skill_id=docker_skill.id, confidence=0.9)
    test_session.add_all([js1, js2, js3])
    await test_session.commit()

    # 3. Create historical snapshot 20 days ago (for trend verification)
    past_day = date.today() - timedelta(days=20)
    past_snap = SkillDemandDaily(
        day=past_day,
        role_query="Python",
        location="Bangalore",
        skill_id=py_skill.id,
        postings_count=1,
        demand_pct=0.50,  # was 50%
    )
    test_session.add(past_snap)
    await test_session.commit()

    # 4. Generate daily snapshot for today
    count = await generate_demand_daily_snapshot(
        test_session,
        target_date=date.today(),
        pairs=[("Python", "Bangalore")],
        window_days=45,
    )
    assert count == 2  # Python and Docker

    # Verify snapshot in DB
    snaps = (
        (await test_session.execute(select(SkillDemandDaily))).scalars().all()
    )
    assert len(snaps) >= 2

    # 5. Query top demanded skills via service
    top_res = await get_top_demanded_skills(
        test_session,
        role_query="Python",
        location="Bangalore",
        limit=10,
        trend_days=30,
    )
    assert top_res.total_postings == 2
    assert len(top_res.skills) == 2

    top_skill = top_res.skills[0]
    assert top_skill.name == "Python"
    assert top_skill.postings_count == 2
    assert top_skill.demand_pct == 1.0
    # Trend: 1.0 (today) - 0.50 (20 days ago) = +0.50
    assert top_skill.trend_pct == 0.50

    # 6. Test GET /api/v1/jobs/skills/top endpoint
    resp = await client.get(
        "/api/v1/jobs/skills/top",
        params={"role": "Python", "location": "Bangalore", "days": 30},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role_query"] == "Python"
    assert data["location"] == "Bangalore"
    assert len(data["skills"]) == 2
    assert data["skills"][0]["name"] == "Python"
    assert data["skills"][0]["demand_pct"] == 1.0


@pytest.mark.asyncio
async def test_scheduler_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    # When disabled
    monkeypatch.setattr(settings, "ENABLE_LOCAL_SCHEDULER", False)
    sched_disabled = start_local_scheduler()
    assert sched_disabled is None

    # When enabled
    monkeypatch.setattr(settings, "ENABLE_LOCAL_SCHEDULER", True)
    sched_enabled = start_local_scheduler()
    assert sched_enabled is not None
    assert sched_enabled.running is True

    # Stop scheduler
    stop_local_scheduler(sched_enabled)
    await asyncio.sleep(0.05)
    assert sched_enabled.running is False

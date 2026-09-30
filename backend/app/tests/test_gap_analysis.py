import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.job import JobPosting, JobSkill
from app.db.models.skill import Skill
from app.db.models.syllabus import Syllabus, SyllabusSkill
from app.db.session import get_db
from app.main import app
from app.services.analysis.gap import compute_gap_analysis
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


@pytest.mark.asyncio
async def test_deterministic_gap_calculation_and_classification(
    test_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)

    # 1. Create Market Skills
    s_python = Skill(canonical_name="Python", category="Languages")
    s_fastapi = Skill(canonical_name="FastAPI", category="Frameworks")
    s_docker = Skill(canonical_name="Docker", category="DevOps")
    s_k8s = Skill(canonical_name="Kubernetes", category="DevOps", aliases=["k8s"])
    s_postgres = Skill(canonical_name="PostgreSQL", category="Databases")
    s_fortran = Skill(canonical_name="Fortran", category="Legacy")

    test_session.add_all([s_python, s_fastapi, s_docker, s_k8s, s_postgres, s_fortran])
    await test_session.flush()

    # 2. Create 4 active job postings for "Backend Developer" in "Bangalore" (P1 source)
    p1 = JobPosting(
        source="adzuna",
        external_id="adz-1",
        title="Senior Backend Developer",
        location="Bangalore",
        description="Python, FastAPI, Docker",
        last_seen_at=now,
        is_expired=False,
    )
    p2 = JobPosting(
        source="adzuna",
        external_id="adz-2",
        title="Backend Developer",
        location="Bangalore",
        description="Python, PostgreSQL",
        last_seen_at=now,
        is_expired=False,
    )
    p3 = JobPosting(
        source="adzuna",
        external_id="adz-3",
        title="Lead Backend Developer",
        location="Bangalore",
        description="Python, Docker, Kubernetes",
        last_seen_at=now,
        is_expired=False,
    )
    p4 = JobPosting(
        source="adzuna",
        external_id="adz-4",
        title="Backend Developer",
        location="Bangalore",
        description="FastAPI, Kubernetes",
        last_seen_at=now,
        is_expired=False,
    )
    test_session.add_all([p1, p2, p3, p4])
    await test_session.flush()

    # Link skills to postings:
    # Python in p1, p2, p3 (3/4 = 0.75)
    # FastAPI in p1, p4 (2/4 = 0.50)
    # Docker in p1, p3 (2/4 = 0.50)
    # Kubernetes in p3, p4 (2/4 = 0.50)
    # PostgreSQL in p2 (1/4 = 0.25)
    # Total market weight = 0.75 + 0.50 + 0.50 + 0.50 + 0.25 = 2.50
    links = [
        JobSkill(job_id=p1.id, skill_id=s_python.id),
        JobSkill(job_id=p1.id, skill_id=s_fastapi.id),
        JobSkill(job_id=p1.id, skill_id=s_docker.id),
        JobSkill(job_id=p2.id, skill_id=s_python.id),
        JobSkill(job_id=p2.id, skill_id=s_postgres.id),
        JobSkill(job_id=p3.id, skill_id=s_python.id),
        JobSkill(job_id=p3.id, skill_id=s_docker.id),
        JobSkill(job_id=p3.id, skill_id=s_k8s.id),
        JobSkill(job_id=p4.id, skill_id=s_fastapi.id),
        JobSkill(job_id=p4.id, skill_id=s_k8s.id),
    ]
    test_session.add_all(links)
    await test_session.flush()

    # 3. Create Syllabus with skills:
    # - Python (exact match -> weight 0.75)
    # - K8s alias skill (alias match to Kubernetes -> weight 0.50)
    # - Fortran (obsolete, 0 market demand -> weight 0.0)
    # Covered weight = 0.75 + 0.50 = 1.25
    # Expected Coverage = (1.25 / 2.50) * 100% = 50.00%
    # Expected Gap = 100 - 50 = 50.00%
    s_k8s_syllabus = Skill(canonical_name="K8s", category="DevOps")
    test_session.add(s_k8s_syllabus)
    await test_session.flush()

    syllabus = Syllabus(
        title="CS201: Web & Distributed Systems",
        filename="cs201.pdf",
        raw_text="Course content covering Python, K8s, and Fortran history.",
        status="ready",
    )
    test_session.add(syllabus)
    await test_session.flush()

    s_links = [
        SyllabusSkill(syllabus_id=syllabus.id, skill_id=s_python.id, evidence="Python"),
        SyllabusSkill(
            syllabus_id=syllabus.id, skill_id=s_k8s_syllabus.id, evidence="K8s"
        ),
        SyllabusSkill(
            syllabus_id=syllabus.id, skill_id=s_fortran.id, evidence="Fortran"
        ),
    ]
    test_session.add_all(s_links)
    await test_session.commit()

    # 4. Compute Gap Analysis
    analysis = await compute_gap_analysis(
        db=test_session,
        syllabus_id=syllabus.id,
        role_query="Backend Developer",
        location="Bangalore",
    )

    # Verify exact deterministic percentages
    assert analysis.coverage_pct == 50.0
    assert analysis.gap_pct == 50.0
    assert analysis.location == "Bangalore"

    # Verify items classification
    covered_items = [it for it in analysis.items if it.kind == "covered"]
    missing_items = [it for it in analysis.items if it.kind == "missing"]
    obsolete_items = [it for it in analysis.items if it.kind == "obsolete"]

    # 2 covered: Python (0.75), Kubernetes (0.50)
    assert len(covered_items) == 2
    covered_names = {it.skill.canonical_name for it in covered_items}
    assert covered_names == {"Python", "Kubernetes"}

    # 3 missing: FastAPI (0.50), Docker (0.50), PostgreSQL (0.25)
    assert len(missing_items) == 3
    missing_names = {it.skill.canonical_name for it in missing_items}
    assert missing_names == {"FastAPI", "Docker", "PostgreSQL"}

    # 1 obsolete: Fortran (0% market demand)
    assert len(obsolete_items) == 1
    assert obsolete_items[0].skill.canonical_name == "Fortran"
    assert obsolete_items[0].demand_pct == 0.0


@pytest.mark.asyncio
async def test_location_and_remote_source_filtering(
    test_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)

    py_skill = Skill(canonical_name="Python")
    go_skill = Skill(canonical_name="Go")
    test_session.add_all([py_skill, go_skill])
    await test_session.flush()

    # P1 Bangalore posting
    p_bangalore = JobPosting(
        source="adzuna",
        external_id="adz-bng",
        title="Cloud Engineer",
        location="Bangalore",
        description="Python cloud",
        last_seen_at=now,
        is_expired=False,
    )
    # P2 Remote posting
    p_remote = JobPosting(
        source="remotive",
        external_id="rem-001",
        title="Cloud Engineer",
        location="Remote",
        description="Go cloud",
        last_seen_at=now,
        is_expired=False,
    )
    test_session.add_all([p_bangalore, p_remote])
    await test_session.flush()

    test_session.add_all(
        [
            JobSkill(job_id=p_bangalore.id, skill_id=py_skill.id),
            JobSkill(job_id=p_remote.id, skill_id=go_skill.id),
        ]
    )

    syllabus = Syllabus(
        title="Cloud Course",
        filename="cloud.pdf",
        raw_text="Cloud",
        status="ready",
    )
    test_session.add(syllabus)
    await test_session.flush()

    test_session.add(
        SyllabusSkill(syllabus_id=syllabus.id, skill_id=py_skill.id, evidence="Python")
    )
    await test_session.commit()

    # 1. Location Bangalore analysis:
    # considers P1 Bangalore posting (Python), not Remote Go
    bng_analysis = await compute_gap_analysis(
        test_session,
        syllabus_id=syllabus.id,
        role_query="Cloud Engineer",
        location="Bangalore",
    )
    assert bng_analysis.coverage_pct == 100.0
    assert bng_analysis.gap_pct == 0.0
    assert len([it for it in bng_analysis.items if it.kind == "covered"]) == 1

    # 2. Remote market analysis:
    # considers P2 Remote posting (Go), where syllabus lacks Go
    remote_analysis = await compute_gap_analysis(
        test_session,
        syllabus_id=syllabus.id,
        role_query="Cloud Engineer",
        remote_only=True,
    )
    assert remote_analysis.coverage_pct == 0.0
    assert remote_analysis.gap_pct == 100.0
    assert len([it for it in remote_analysis.items if it.kind == "missing"]) == 1


@pytest.mark.asyncio
async def test_analysis_api_endpoints(
    client: AsyncClient,
    test_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    skill = Skill(canonical_name="Rust")
    test_session.add(skill)
    await test_session.flush()

    posting = JobPosting(
        source="fixture",
        external_id="fix-rust-1",
        title="Rust Systems Engineer",
        location="Bangalore",
        description="Rust systems",
        last_seen_at=now,
        is_expired=False,
    )
    test_session.add(posting)
    await test_session.flush()

    test_session.add(JobSkill(job_id=posting.id, skill_id=skill.id))

    syllabus = Syllabus(
        title="Systems Programming",
        filename="sys.docx",
        raw_text="Rust programming",
        status="ready",
    )
    test_session.add(syllabus)
    await test_session.flush()

    test_session.add(
        SyllabusSkill(syllabus_id=syllabus.id, skill_id=skill.id, evidence="Rust")
    )
    await test_session.commit()

    # POST /api/v1/analysis
    create_resp = await client.post(
        "/api/v1/analysis",
        json={
            "syllabus_id": str(syllabus.id),
            "role_query": "Rust Systems Engineer",
            "location": "Bangalore",
        },
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["coverage_pct"] == 100.0
    assert created_data["gap_pct"] == 0.0
    analysis_id = created_data["id"]

    # GET /api/v1/analysis/{id}
    get_resp = await client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == analysis_id
    assert len(get_data["items"]) >= 1
    assert get_data["items"][0]["skill_name"] == "Rust"
    assert get_data["items"][0]["kind"] == "covered"

    # GET /api/v1/analysis list
    list_resp = await client.get(
        "/api/v1/analysis",
        params={"syllabus_id": str(syllabus.id)},
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert len(list_data) == 1

    # Non-existent syllabus -> 404
    fake_id = str(uuid.uuid4())
    bad_resp = await client.post(
        "/api/v1/analysis",
        json={"syllabus_id": fake_id, "role_query": "Engineer"},
    )
    assert bad_resp.status_code == 404

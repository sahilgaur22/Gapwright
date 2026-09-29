from collections.abc import AsyncGenerator
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import (
    Analysis,
    AnalysisItem,
    ApiUsage,
    CrawlState,
    Institution,
    JobPosting,
    JobSkill,
    JobSource,
    Skill,
    SkillDemandDaily,
    Syllabus,
    SyllabusSkill,
    User,
)


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    # In-memory SQLite async engine
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


@pytest.mark.asyncio
async def test_institution_and_user_creation(test_session: AsyncSession) -> None:
    inst = Institution(name="Tech Institute", city="Bangalore")
    test_session.add(inst)
    await test_session.flush()

    user = User(
        email="educator@tech.edu",
        password_hash="hashed_pw",
        role="educator",
        institution_id=inst.id,
    )
    test_session.add(user)
    await test_session.commit()

    result = await test_session.execute(
        select(User).where(User.email == "educator@tech.edu")
    )
    fetched_user = result.scalar_one()
    assert fetched_user.id is not None
    assert fetched_user.role == "educator"
    assert fetched_user.institution_id == inst.id


@pytest.mark.asyncio
async def test_syllabus_and_skill_association(test_session: AsyncSession) -> None:
    syllabus = Syllabus(
        title="Distributed Systems",
        department="Computer Science",
        filename="distributed_systems.pdf",
        raw_text="Course content covering Paxos, Raft, and RPCs.",
        status="uploaded",
    )
    skill = Skill(
        canonical_name="Distributed Consensus",
        category="Backend Architecture",
        aliases=["Consensus Protocols", "Raft"],
    )
    test_session.add_all([syllabus, skill])
    await test_session.flush()

    association = SyllabusSkill(
        syllabus_id=syllabus.id,
        skill_id=skill.id,
        evidence="Topic covered in Module 3",
        confidence=0.95,
    )
    test_session.add(association)
    await test_session.commit()

    result = await test_session.execute(
        select(SyllabusSkill).where(SyllabusSkill.syllabus_id == syllabus.id)
    )
    assoc_record = result.scalar_one()
    assert assoc_record.confidence == 0.95
    assert assoc_record.skill_id == skill.id


@pytest.mark.asyncio
async def test_job_posting_and_analysis_models(test_session: AsyncSession) -> None:
    source = JobSource(
        name="adzuna",
        priority=1,
        enabled=True,
        attribution_text="Jobs by Adzuna",
        attribution_url="https://www.adzuna.in",
        may_display_listing=True,
    )
    test_session.add(source)
    await test_session.flush()

    job = JobPosting(
        source="adzuna",
        external_id="adzuna-12345",
        title="Backend Engineer",
        company="Acme Corp",
        location="Bangalore",
        description="Looking for Python and FastAPI expert.",
        description_is_truncated=False,
    )
    crawl_state = CrawlState(
        source="adzuna",
        role_query="Backend Engineer",
        location="Bangalore",
    )
    api_usage = ApiUsage(
        source="adzuna",
        day=date.today(),
        calls=1,
    )
    test_session.add_all([job, crawl_state, api_usage])
    await test_session.flush()

    skill = Skill(canonical_name="Python", category="Programming Languages")
    test_session.add(skill)
    await test_session.flush()

    job_skill = JobSkill(job_id=job.id, skill_id=skill.id, confidence=1.0)
    demand = SkillDemandDaily(
        day=date.today(),
        role_query="Backend Engineer",
        location="Bangalore",
        skill_id=skill.id,
        postings_count=10,
        demand_pct=0.45,
    )
    test_session.add_all([job_skill, demand])
    await test_session.flush()

    syllabus = Syllabus(
        title="CS101",
        filename="cs101.pdf",
        raw_text="Intro Python",
    )
    test_session.add(syllabus)
    await test_session.flush()

    analysis = Analysis(
        syllabus_id=syllabus.id,
        role_query="Backend Engineer",
        location="Bangalore",
        gap_pct=35.0,
        coverage_pct=65.0,
    )
    test_session.add(analysis)
    await test_session.flush()

    item = AnalysisItem(
        analysis_id=analysis.id,
        skill_id=skill.id,
        kind="covered",
        demand_count=10,
        demand_pct=0.45,
        rank=1,
    )
    test_session.add(item)
    await test_session.commit()

    # Query back analysis and item
    result = await test_session.execute(
        select(Analysis).where(Analysis.id == analysis.id)
    )
    saved_analysis = result.scalar_one()
    assert saved_analysis.gap_pct == 35.0
    assert saved_analysis.coverage_pct == 65.0

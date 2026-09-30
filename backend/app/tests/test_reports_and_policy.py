"""Tests for CSV/PDF report exports and policymaker overview endpoints."""

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.db.base import Base
from app.db.models.analysis import Analysis, AnalysisItem
from app.db.models.skill import Skill
from app.db.models.syllabus import Syllabus
from app.db.models.user import Institution, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
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
async def analysis_fixture(test_session: AsyncSession) -> tuple[Analysis, Syllabus]:
    """Create a sample Syllabus and Analysis for reporting tests."""
    inst = Institution(
        id=uuid.uuid4(),
        name="Indian Institute of Technology, Madras",
        city="Chennai",
    )
    test_session.add(inst)
    await test_session.flush()

    syl = Syllabus(
        id=uuid.uuid4(),
        title="B.Tech Computer Science - Distributed Systems",
        department="Computer Science",
        filename="distributed_systems.pdf",
        institution_id=inst.id,
        raw_text="Sample syllabus text...",
        status="ready",
    )
    test_session.add(syl)
    await test_session.flush()

    s1 = Skill(
        id=uuid.uuid4(),
        canonical_name="Distributed Consensus",
        category="Systems",
    )
    s2 = Skill(
        id=uuid.uuid4(),
        canonical_name="Kubernetes",
        category="DevOps",
    )
    s3 = Skill(
        id=uuid.uuid4(),
        canonical_name="CORBA",
        category="Legacy Architecture",
    )
    test_session.add_all([s1, s2, s3])
    await test_session.flush()

    analysis = Analysis(
        id=uuid.uuid4(),
        syllabus_id=syl.id,
        role_query="Cloud Systems Engineer",
        location="Bengaluru",
        gap_pct=33.3,
        coverage_pct=66.7,
    )
    test_session.add(analysis)
    await test_session.flush()

    item1 = AnalysisItem(
        analysis_id=analysis.id,
        skill_id=s1.id,
        kind="covered",
        demand_count=45,
        demand_pct=60.0,
        rank=1,
    )
    item2 = AnalysisItem(
        analysis_id=analysis.id,
        skill_id=s2.id,
        kind="missing",
        demand_count=40,
        demand_pct=53.3,
        rank=2,
    )
    item3 = AnalysisItem(
        analysis_id=analysis.id,
        skill_id=s3.id,
        kind="obsolete",
        demand_count=2,
        demand_pct=2.7,
        rank=20,
    )
    test_session.add_all([item1, item2, item3])
    await test_session.commit()
    await test_session.refresh(analysis)

    return analysis, syl


@pytest.fixture
async def users_fixture(test_session: AsyncSession) -> dict[str, str]:
    """Create users with student, educator, and policymaker roles and return tokens."""
    roles = ["student", "educator", "policymaker", "admin"]
    tokens = {}

    for r in roles:
        u = User(
            id=uuid.uuid4(),
            email=f"{r}_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="hashed_pw_test",
            role=r,
        )
        test_session.add(u)
        await test_session.flush()
        tokens[r] = create_access_token(subject=str(u.id))

    await test_session.commit()
    return tokens


@pytest.mark.asyncio
async def test_export_analysis_report_csv(
    client: AsyncClient,
    analysis_fixture: tuple[Analysis, Syllabus],
) -> None:
    """Test exporting an analysis report as a CSV file."""
    analysis, _ = analysis_fixture

    resp = await client.get(f"/api/v1/reports/{analysis.id}/export?format=csv")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    expected_csv_fn = f'filename="gapwright-analysis-{analysis.id}.csv"'
    assert expected_csv_fn in resp.headers["content-disposition"]

    content = resp.text
    assert "Gapwright - Curriculum Gap Analysis Report" in content
    assert "Cloud Systems Engineer" in content
    assert "Distributed Consensus" in content
    assert "Kubernetes" in content
    assert "Covered" in content
    assert "Missing" in content


@pytest.mark.asyncio
async def test_export_analysis_report_pdf(
    client: AsyncClient,
    analysis_fixture: tuple[Analysis, Syllabus],
) -> None:
    """Test exporting an analysis report as a PDF file."""
    analysis, _ = analysis_fixture

    resp = await client.get(f"/api/v1/reports/{analysis.id}/export?format=pdf")

    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    expected_pdf_fn = f'filename="gapwright-analysis-{analysis.id}.pdf"'
    assert expected_pdf_fn in resp.headers["content-disposition"]
    # PDF magic bytes
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


@pytest.mark.asyncio
async def test_export_analysis_report_unsupported_format(
    client: AsyncClient,
    analysis_fixture: tuple[Analysis, Syllabus],
) -> None:
    """Test requesting an invalid export format."""
    analysis, _ = analysis_fixture

    resp = await client.get(f"/api/v1/reports/{analysis.id}/export?format=xml")

    assert resp.status_code == 400
    assert "Unsupported format" in resp.text


@pytest.mark.asyncio
async def test_policy_overview_requires_auth(client: AsyncClient) -> None:
    """Test that /policy/overview returns 401 without authentication."""
    resp = await client.get("/api/v1/policy/overview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_policy_overview_role_guard(
    client: AsyncClient,
    users_fixture: dict[str, str],
) -> None:
    """Test that student and educator roles are rejected with 403 Forbidden."""
    # Student
    resp_student = await client.get(
        "/api/v1/policy/overview",
        headers={"Authorization": f"Bearer {users_fixture['student']}"},
    )
    assert resp_student.status_code == 403
    assert "Access forbidden" in resp_student.text

    # Educator
    resp_educator = await client.get(
        "/api/v1/policy/overview",
        headers={"Authorization": f"Bearer {users_fixture['educator']}"},
    )
    assert resp_educator.status_code == 403


@pytest.mark.asyncio
async def test_policy_overview_authorized_policymaker(
    client: AsyncClient,
    analysis_fixture: tuple[Analysis, Syllabus],
    users_fixture: dict[str, str],
) -> None:
    """Test that policymaker role gets 200 OK with systemic aggregations."""
    resp = await client.get(
        "/api/v1/policy/overview",
        headers={"Authorization": f"Bearer {users_fixture['policymaker']}"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["total_analyses"] >= 1
    assert data["total_institutions"] >= 1
    assert "average_gap_pct" in data
    assert "average_coverage_pct" in data
    assert isinstance(data["top_systemic_missing_skills"], list)

    # Kubernetes was marked as missing in analysis_fixture
    missing_skill_names = [s["skill_name"] for s in data["top_systemic_missing_skills"]]
    assert "Kubernetes" in missing_skill_names

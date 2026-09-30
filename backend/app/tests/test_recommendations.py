import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.analysis import Analysis, AnalysisItem
from app.db.models.job import SkillDemandDaily
from app.db.models.skill import Skill
from app.db.models.syllabus import Syllabus
from app.db.session import get_db
from app.main import app
from app.schemas.analysis import SkillRecommendationAction
from app.services.analysis.recommendations import generate_curriculum_recommendations
from app.services.llm.base import LLMProvider
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
async def test_curriculum_recommendations_rule_based_fallback(
    test_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)

    # 1. Setup Skills
    s_docker = Skill(canonical_name="Docker", category="DevOps")
    s_fastapi = Skill(canonical_name="FastAPI", category="Frameworks")
    s_pascal = Skill(canonical_name="Pascal", category="Legacy")
    s_cobol = Skill(canonical_name="COBOL", category="Legacy")
    test_session.add_all([s_docker, s_fastapi, s_pascal, s_cobol])
    await test_session.flush()

    # 2. Historical demand snaps for 30-day trend calculation
    # Docker demand grew from 20% to 50% (+30%)
    # FastAPI demand steady at 40% (0%)
    test_session.add_all(
        [
            SkillDemandDaily(
                day=(now - timedelta(days=25)).date(),
                role_query="Backend Engineer",
                location="San Francisco",
                skill_id=s_docker.id,
                postings_count=20,
                demand_pct=0.20,
            ),
            SkillDemandDaily(
                day=now.date(),
                role_query="Backend Engineer",
                location="San Francisco",
                skill_id=s_docker.id,
                postings_count=50,
                demand_pct=0.50,
            ),
            SkillDemandDaily(
                day=(now - timedelta(days=20)).date(),
                role_query="Backend Engineer",
                location="San Francisco",
                skill_id=s_fastapi.id,
                postings_count=40,
                demand_pct=0.40,
            ),
            SkillDemandDaily(
                day=now.date(),
                role_query="Backend Engineer",
                location="San Francisco",
                skill_id=s_fastapi.id,
                postings_count=40,
                demand_pct=0.40,
            ),
        ]
    )

    # 3. Create Syllabus and Analysis record
    syllabus = Syllabus(
        title="Modern Software Engineering",
        filename="swe.pdf",
        raw_text="Pascal and COBOL foundations.",
        status="ready",
    )
    test_session.add(syllabus)
    await test_session.flush()

    analysis = Analysis(
        syllabus_id=syllabus.id,
        role_query="Backend Engineer",
        location="San Francisco",
        gap_pct=75.0,
        coverage_pct=25.0,
    )
    test_session.add(analysis)
    await test_session.flush()

    # Analysis items: Docker (missing 50%), FastAPI (missing 40%),
    # Pascal (obsolete 0%), COBOL (obsolete 5%)
    items = [
        AnalysisItem(
            analysis_id=analysis.id,
            skill_id=s_docker.id,
            kind="missing",
            demand_count=50,
            demand_pct=0.50,
            rank=1,
        ),
        AnalysisItem(
            analysis_id=analysis.id,
            skill_id=s_fastapi.id,
            kind="missing",
            demand_count=40,
            demand_pct=0.40,
            rank=2,
        ),
        AnalysisItem(
            analysis_id=analysis.id,
            skill_id=s_pascal.id,
            kind="obsolete",
            demand_count=0,
            demand_pct=0.0,
            rank=3,
        ),
        AnalysisItem(
            analysis_id=analysis.id,
            skill_id=s_cobol.id,
            kind="obsolete",
            demand_count=5,
            demand_pct=0.05,
            rank=4,
        ),
    ]
    test_session.add_all(items)
    await test_session.commit()

    # 4. Run recommendations without LLM provider (fallback mode)
    result = await generate_curriculum_recommendations(
        db=test_session,
        analysis_id=analysis.id,
        llm_provider=None,
        max_add=5,
        max_drop=5,
    )

    assert result.analysis_id == analysis.id
    assert result.course_title == "Modern Software Engineering"
    assert result.gap_pct == 75.0
    assert len(result.skills_to_add) == 2
    assert len(result.skills_to_drop) == 2

    # Verify Add recommendations: Docker has higher demand & positive trend
    top_add = result.skills_to_add[0]
    assert top_add.skill_name == "Docker"
    assert top_add.action == SkillRecommendationAction.ADD
    assert top_add.demand_pct == 0.50
    assert top_add.trend_pct == 0.30
    assert top_add.suggested_weeks > 0

    second_add = result.skills_to_add[1]
    assert second_add.skill_name == "FastAPI"
    assert second_add.action == SkillRecommendationAction.ADD

    # Verify Drop recommendations: Pascal (0% demand) prioritized before COBOL
    assert result.skills_to_drop[0].skill_name == "Pascal"
    assert result.skills_to_drop[0].action == SkillRecommendationAction.DROP
    assert result.skills_to_drop[0].demand_pct == 0.0

    assert result.skills_to_drop[1].skill_name == "COBOL"
    assert result.skills_to_drop[1].action == SkillRecommendationAction.DROP


@pytest.mark.asyncio
async def test_curriculum_recommendations_with_mocked_llm(
    test_session: AsyncSession,
) -> None:
    # 1. Setup Skills and Analysis
    s_k8s = Skill(canonical_name="Kubernetes", category="DevOps")
    s_perl = Skill(canonical_name="Perl", category="Legacy")
    test_session.add_all([s_k8s, s_perl])
    await test_session.flush()

    syllabus = Syllabus(
        title="Infrastructure Systems",
        filename="infra.docx",
        raw_text="Intro to Perl.",
        status="ready",
    )
    test_session.add(syllabus)
    await test_session.flush()

    analysis = Analysis(
        syllabus_id=syllabus.id,
        role_query="DevOps Engineer",
        location="Bangalore",
        gap_pct=60.0,
        coverage_pct=40.0,
    )
    test_session.add(analysis)
    await test_session.flush()

    test_session.add_all(
        [
            AnalysisItem(
                analysis_id=analysis.id,
                skill_id=s_k8s.id,
                kind="missing",
                demand_count=30,
                demand_pct=0.60,
            ),
            AnalysisItem(
                analysis_id=analysis.id,
                skill_id=s_perl.id,
                kind="obsolete",
                demand_count=0,
                demand_pct=0.0,
            ),
        ]
    )
    await test_session.commit()

    # 2. Mock LLMProvider
    mock_llm = AsyncMock(spec=LLMProvider)
    summary_text = "Modernize the infrastructure syllabus with container orchestration."
    mock_llm.extract_json.return_value = {
        "summary": summary_text,
        "skills_to_add": [
            {
                "name": "Kubernetes",
                "rationale": "Essential for container orchestration in modern clouds.",
                "suggested_module": "Cloud Native Orchestration",
                "suggested_weeks": 3,
            }
        ],
        "skills_to_drop": [
            {
                "name": "Perl",
                "rationale": "Superseded by Python and Go for automation.",
            }
        ],
    }

    # 3. Call service
    result = await generate_curriculum_recommendations(
        db=test_session,
        analysis_id=analysis.id,
        llm_provider=mock_llm,
    )

    assert result.summary == summary_text
    assert len(result.skills_to_add) == 1
    assert result.skills_to_add[0].skill_name == "Kubernetes"
    assert result.skills_to_add[0].suggested_module == "Cloud Native Orchestration"
    assert result.skills_to_add[0].suggested_weeks == 3
    assert (
        result.skills_to_add[0].rationale
        == "Essential for container orchestration in modern clouds."
    )

    assert len(result.skills_to_drop) == 1
    assert result.skills_to_drop[0].skill_name == "Perl"
    assert (
        result.skills_to_drop[0].rationale
        == "Superseded by Python and Go for automation."
    )


@pytest.mark.asyncio
async def test_get_recommendations_endpoint(
    client: AsyncClient,
    test_session: AsyncSession,
) -> None:
    # 1. Create entities
    skill = Skill(canonical_name="TypeScript", category="Frontend")
    test_session.add(skill)
    await test_session.flush()

    syllabus = Syllabus(
        title="Web Architecture",
        filename="web.pdf",
        raw_text="Web syllabus",
        status="ready",
    )
    test_session.add(syllabus)
    await test_session.flush()

    analysis = Analysis(
        syllabus_id=syllabus.id,
        role_query="Frontend Engineer",
        location="Remote",
        gap_pct=45.0,
        coverage_pct=55.0,
    )
    test_session.add(analysis)
    await test_session.flush()

    test_session.add(
        AnalysisItem(
            analysis_id=analysis.id,
            skill_id=skill.id,
            kind="missing",
            demand_count=15,
            demand_pct=0.45,
        )
    )
    await test_session.commit()

    # 2. Query endpoint
    resp = await client.get(f"/api/v1/analysis/{analysis.id}/recommendations")
    assert resp.status_code == 200
    data = resp.json()

    assert data["analysis_id"] == str(analysis.id)
    assert data["course_title"] == "Web Architecture"
    assert data["gap_pct"] == 45.0
    assert len(data["skills_to_add"]) == 1
    assert data["skills_to_add"][0]["skill_name"] == "TypeScript"
    assert data["skills_to_add"][0]["action"] == "add"

    # 3. 404 for unknown analysis ID
    random_id = str(uuid.uuid4())
    bad_resp = await client.get(f"/api/v1/analysis/{random_id}/recommendations")
    assert bad_resp.status_code == 404

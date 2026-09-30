import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.skill import Skill
from app.schemas.analysis import MatchType
from app.services.analysis.matcher import (
    compute_cosine_similarity,
    find_semantic_matches_in_db,
    is_alias_match,
    match_all_skills,
    match_single_skill,
)


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


def test_compute_cosine_similarity() -> None:
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v1) == 1.0

    # Orthogonal vectors
    v2 = [0.0, 1.0, 0.0]
    assert compute_cosine_similarity(v1, v2) == 0.0

    # Opposite vectors
    v3 = [-1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v3) == -1.0

    # Partial similarity
    v4 = [1.0, 1.0, 0.0]
    sim = compute_cosine_similarity(v1, v4)
    assert round(sim, 4) == 0.7071

    # Edge cases
    assert compute_cosine_similarity(None, v1) == 0.0
    assert compute_cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert compute_cosine_similarity([1.0, 2.0], [1.0]) == 0.0


def test_is_alias_match() -> None:
    # Exact case-insensitive
    assert is_alias_match("FastAPI", [], "fastapi", []) is True

    # Seed taxonomy alias lookup
    assert is_alias_match("K8s", [], "Kubernetes", []) is True
    assert is_alias_match("NLP", [], "Natural Language Processing", []) is True

    # Custom aliases
    assert is_alias_match("Postgres", ["PostgreSQL"], "PostgreSQL", []) is True
    assert is_alias_match("React", ["ReactJS"], "React Native", ["ReactJS"]) is True

    # Completely unrelated
    assert is_alias_match("Python", [], "Gardening", []) is False
    assert is_alias_match("Docker", [], "Cooking", []) is False


def test_match_single_skill_exact_and_alias() -> None:
    s_python = Skill(
        id=uuid.uuid4(),
        canonical_name="Python",
        aliases=["py"],
    )
    s_k8s = Skill(
        id=uuid.uuid4(),
        canonical_name="K8s",
        aliases=[],
    )

    m_python = Skill(
        id=uuid.uuid4(),
        canonical_name="python",
        aliases=[],
    )
    m_kubernetes = Skill(
        id=uuid.uuid4(),
        canonical_name="Kubernetes",
        aliases=["k8s"],
    )
    m_docker = Skill(
        id=uuid.uuid4(),
        canonical_name="Docker",
        aliases=[],
    )

    market = [m_python, m_kubernetes, m_docker]

    # Exact match test
    res_py = match_single_skill(s_python, market)
    assert res_py is not None
    assert res_py.match_type == MatchType.EXACT
    assert res_py.similarity == 1.0
    assert res_py.market_skill_id == m_python.id

    # Alias match test
    res_k8s = match_single_skill(s_k8s, market)
    assert res_k8s is not None
    assert res_k8s.match_type == MatchType.ALIAS
    assert res_k8s.similarity == 1.0
    assert res_k8s.market_skill_id == m_kubernetes.id


def test_match_single_skill_semantic_and_unrelated() -> None:
    # 3-dim vectors for demonstration
    # Skill A (FastAPI): [0.95, 0.1, 0.05]
    # Skill B (Flask - near match): [0.92, 0.15, 0.05] -> sim > 0.99
    # Skill C (Gardening - completely unrelated): [0.01, 0.98, 0.1] -> low sim
    s_fastapi = Skill(
        id=uuid.uuid4(),
        canonical_name="FastAPI Framework",
        aliases=[],
        embedding=[0.95, 0.1, 0.05],
    )
    s_database = Skill(
        id=uuid.uuid4(),
        canonical_name="Relational Database Architecture",
        aliases=[],
        embedding=[0.05, 0.1, 0.95],
    )

    m_flask = Skill(
        id=uuid.uuid4(),
        canonical_name="Flask Framework",
        aliases=[],
        embedding=[0.92, 0.15, 0.05],
    )
    m_gardening = Skill(
        id=uuid.uuid4(),
        canonical_name="Organic Gardening",
        aliases=[],
        embedding=[0.01, 0.98, 0.1],
    )

    market = [m_flask, m_gardening]

    # Semantic near-match should succeed
    res_fastapi = match_single_skill(s_fastapi, market, threshold=0.85)
    assert res_fastapi is not None
    assert res_fastapi.match_type == MatchType.SEMANTIC
    assert res_fastapi.market_skill_id == m_flask.id
    assert res_fastapi.similarity >= 0.85

    # Unrelated skill should have NO false positives!
    res_db = match_single_skill(s_database, market, threshold=0.85)
    assert res_db is None


def test_match_all_skills_batch() -> None:
    s1 = Skill(id=uuid.uuid4(), canonical_name="Python")
    s2 = Skill(id=uuid.uuid4(), canonical_name="NLP")
    s3 = Skill(
        id=uuid.uuid4(),
        canonical_name="Obsolete Skill",
        embedding=[0.1, 0.1, 0.1],
    )

    m1 = Skill(id=uuid.uuid4(), canonical_name="Python")
    m2 = Skill(id=uuid.uuid4(), canonical_name="Natural Language Processing")
    m3 = Skill(
        id=uuid.uuid4(),
        canonical_name="Different Modern Tech",
        embedding=[0.9, 0.0, 0.0],
    )

    syllabus = [s1, s2, s3]
    market = [m1, m2, m3]

    matches = match_all_skills(syllabus, market, threshold=0.85)
    assert len(matches) == 2
    match_map = {m.syllabus_skill_name: m.match_type for m in matches}
    assert match_map["Python"] == MatchType.EXACT
    assert match_map["NLP"] == MatchType.ALIAS


@pytest.mark.asyncio
async def test_find_semantic_matches_in_db(test_session: AsyncSession) -> None:
    target = Skill(
        canonical_name="Deep Learning",
        category="AI",
        embedding=[0.90, 0.20, 0.10],
    )
    near_match = Skill(
        canonical_name="Neural Networks",
        category="AI",
        embedding=[0.88, 0.22, 0.12],
    )
    unrelated = Skill(
        canonical_name="Pottery Craft",
        category="Arts",
        embedding=[0.05, 0.95, 0.10],
    )

    test_session.add_all([target, near_match, unrelated])
    await test_session.commit()

    matches = await find_semantic_matches_in_db(
        test_session,
        target,
        limit=5,
        threshold=0.85,
    )
    assert len(matches) == 1
    matched_skill, sim = matches[0]
    assert matched_skill.canonical_name == "Neural Networks"
    assert sim >= 0.85

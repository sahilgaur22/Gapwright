from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.schemas.skill import SkillExtractionItem
from app.services.llm.base import LLMProvider
from app.services.skills.normalizer import (
    cosine_similarity,
    normalize_skill,
    normalize_skills_batch,
    seed_skills_taxonomy,
)


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
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


class MockEmbedProvider:
    """Mock LLMProvider providing deterministic vector embeddings for testing."""

    def __init__(self, vector_map: dict[str, list[float]]) -> None:
        self.vector_map = vector_map
        self.default_vector = [0.0] * 768

    @property
    def provider_name(self) -> str:
        return "mock-embed"

    @property
    def model_name(self) -> str:
        return "mock-embed-model"

    async def extract_json(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return {}

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        if isinstance(text, str):
            return self.vector_map.get(text.lower(), self.default_vector)
        return [self.vector_map.get(t.lower(), self.default_vector) for t in text]


def test_cosine_similarity() -> None:
    # Identical vectors
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6
    # Orthogonal vectors
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.0) < 1e-6
    # Opposite vectors
    assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-6
    # Empty or mismatched
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


@pytest.mark.asyncio
async def test_k8s_kubernetes_resolve_to_single_node(
    test_session: AsyncSession,
) -> None:
    # Seed the standard taxonomy into the database
    seeded_count = await seed_skills_taxonomy(test_session)
    assert seeded_count > 50

    # 1. Normalize "Kubernetes"
    node_1 = await normalize_skill("Kubernetes", "Cloud & DevOps", test_session)
    assert node_1.canonical_name == "Kubernetes"

    # 2. Normalize "K8s"
    node_2 = await normalize_skill("K8s", "DevOps", test_session)
    assert node_2.id == node_1.id
    assert node_2.canonical_name == "Kubernetes"

    # 3. Normalize "kubernetes orchestration"
    node_3 = await normalize_skill("kubernetes orchestration", "Cloud", test_session)
    assert node_3.id == node_1.id
    assert node_3.canonical_name == "Kubernetes"


@pytest.mark.asyncio
async def test_nlp_alias_normalization(test_session: AsyncSession) -> None:
    await seed_skills_taxonomy(test_session)

    nlp_node = await normalize_skill("NLP", "AI", test_session)
    assert nlp_node.canonical_name == "Natural Language Processing"
    assert nlp_node.category == "Machine Learning"

    full_node = await normalize_skill(
        "Natural Language Processing", "Machine Learning", test_session
    )
    assert full_node.id == nlp_node.id


@pytest.mark.asyncio
async def test_semantic_embedding_merge_with_threshold(
    test_session: AsyncSession,
) -> None:
    # Setup mock vectors with cosine similarity > 0.85
    # Vector A: [1.0, 0.0, 0.0]
    # Vector B (near synonym): [0.95, 0.31, 0.0] -> cos sim ~ 0.95
    # Vector C (unrelated): [0.0, 1.0, 0.0] -> cos sim = 0.0
    vector_map = {
        "graphql": [1.0, 0.0, 0.0] + [0.0] * 765,
        "graphql query language": [0.95, 0.31, 0.0] + [0.0] * 765,
        "unrelated technology xyz": [0.0, 1.0, 0.0] + [0.0] * 765,
    }
    embed_provider = MockEmbedProvider(vector_map)
    assert isinstance(embed_provider, LLMProvider)

    # 1. Create base skill with embedding
    base_skill = await normalize_skill(
        "GraphQL",
        "Frameworks",
        test_session,
        embed_provider=embed_provider,
    )
    assert base_skill.canonical_name == "GraphQL"

    # 2. Normalize "graphql query language" (not in alias map, cos sim >= 0.85)
    matched_skill = await normalize_skill(
        "graphql query language",
        "APIs",
        test_session,
        embed_provider=embed_provider,
        threshold=0.85,
    )
    assert matched_skill.id == base_skill.id
    assert matched_skill.canonical_name == "GraphQL"

    # 3. Normalize "unrelated technology xyz" (cosine sim = 0.0 < 0.85)
    new_skill = await normalize_skill(
        "unrelated technology xyz",
        "Misc",
        test_session,
        embed_provider=embed_provider,
        threshold=0.85,
    )
    assert new_skill.id != base_skill.id
    assert new_skill.canonical_name == "unrelated technology xyz"


@pytest.mark.asyncio
async def test_normalize_skills_batch(test_session: AsyncSession) -> None:
    await seed_skills_taxonomy(test_session)

    items = [
        SkillExtractionItem(
            name="Python",
            category="Languages",
            evidence="Python programming",
            confidence=0.98,
        ),
        SkillExtractionItem(
            name="k8s",
            category="Cloud",
            evidence="Deploying to k8s",
            confidence=0.90,
        ),
        SkillExtractionItem(
            name="postgres",
            category="DB",
            evidence="PostgreSQL queries",
            confidence=0.92,
        ),
    ]

    pairs = await normalize_skills_batch(items, test_session)
    assert len(pairs) == 3

    node_names = [p[0].canonical_name for p in pairs]
    assert "Python" in node_names
    assert "Kubernetes" in node_names
    assert "PostgreSQL" in node_names

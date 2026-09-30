import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.db.base import Base
from app.db.models.syllabus import Syllabus
from app.db.models.user import Institution, User
from app.db.session import get_db
from app.main import app
from app.services.llm.base import LLMProvider
from app.services.llm.exceptions import ModelResponseError
from app.services.skills.pipeline import process_syllabus_pipeline


class MockLLMProvider(LLMProvider):
    def __init__(
        self,
        extraction_data: dict[str, Any] | list[dict[str, Any]],
        should_fail: bool = False,
        error_msg: str = "Provider quota exhausted",
    ) -> None:
        self.extraction_data = extraction_data
        self.should_fail = should_fail
        self.error_msg = error_msg
        self.calls: list[str] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def extract_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        self.calls.append(prompt)
        if self.should_fail:
            raise ModelResponseError(self.error_msg)
        return self.extraction_data

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        import hashlib

        if isinstance(text, list):
            res: list[list[float]] = []
            for item in text:
                digest = hashlib.md5(item.strip().lower().encode()).hexdigest()
                idx = int(digest, 16) % 768
                vec = [0.0] * 768
                vec[idx] = 1.0
                res.append(vec)
            return res

        idx = int(hashlib.md5(text.strip().lower().encode()).hexdigest(), 16) % 768
        vec = [0.0] * 768
        vec[idx] = 1.0
        return vec


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


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_test_user(
    session: AsyncSession,
    email: str,
    *,
    institution_id: uuid.UUID | None = None,
) -> tuple[User, str]:
    user = User(
        email=email,
        password_hash="testpasshash",
        role="educator",
        institution_id=institution_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = create_access_token(user.id)
    return user, token


@pytest.mark.asyncio
async def test_syllabus_pipeline_end_to_end_success(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    inst = Institution(name="Stanford University", city="Stanford")
    test_session.add(inst)
    await test_session.commit()
    await test_session.refresh(inst)

    user, token = await _create_test_user(
        test_session, "prof@stanford.edu", institution_id=inst.id
    )

    raw_text = (
        "CS 240: Advanced Topics in Operating Systems.\n"
        "Students will work with Python scripting and k8s for cluster management.\n"
        "Hands-on exercises with PostgreSQL databases and Docker containers."
    )
    syllabus = Syllabus(
        id=uuid.uuid4(),
        institution_id=inst.id,
        uploaded_by=user.id,
        title="Advanced OS",
        department="Computer Science",
        filename="cs240.pdf",
        raw_text=raw_text,
        status="uploaded",
    )
    test_session.add(syllabus)
    await test_session.commit()
    await test_session.refresh(syllabus)

    mock_llm = MockLLMProvider(
        extraction_data={
            "skills": [
                {
                    "name": "Python",
                    "category": "Languages",
                    "evidence": "Students will work with Python scripting",
                    "confidence": 0.95,
                },
                {
                    "name": "k8s",
                    "category": "Cloud/DevOps",
                    "evidence": "k8s for cluster management",
                    "confidence": 0.90,
                },
                {
                    "name": "PostgreSQL",
                    "category": "Databases",
                    "evidence": "Hands-on exercises with PostgreSQL databases",
                    "confidence": 0.88,
                },
            ]
        }
    )

    # Run the pipeline
    processed = await process_syllabus_pipeline(
        syllabus.id,
        db=test_session,
        provider=mock_llm,
    )

    assert processed.status == "ready"
    assert processed.error_message is None

    # Verify through API endpoint GET /syllabi/{id}/skills
    response = await client.get(
        f"/api/v1/syllabi/{syllabus.id}/skills",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["syllabus_id"] == str(syllabus.id)
    assert data["status"] == "ready"
    assert data["error_message"] is None
    assert data["total"] == 3

    skill_names = [s["canonical_name"] for s in data["skills"]]
    # Notice 'k8s' was normalized to canonical 'Kubernetes'
    assert "Kubernetes" in skill_names
    assert "Python" in skill_names
    assert "PostgreSQL" in skill_names

    # Check evidence on Kubernetes
    k8s_skill = next(s for s in data["skills"] if s["canonical_name"] == "Kubernetes")
    assert k8s_skill["evidence"] == "k8s for cluster management"
    assert k8s_skill["confidence"] == 0.90


@pytest.mark.asyncio
async def test_syllabus_pipeline_failure_path_recorded(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    inst = Institution(name="MIT", city="Cambridge")
    test_session.add(inst)
    await test_session.commit()
    await test_session.refresh(inst)

    user, token = await _create_test_user(
        test_session, "faculty@mit.edu", institution_id=inst.id
    )

    syllabus = Syllabus(
        id=uuid.uuid4(),
        institution_id=inst.id,
        uploaded_by=user.id,
        title="Quantum Algorithms",
        department="Physics",
        filename="quantum.pdf",
        raw_text="Quantum computing fundamentals and Qiskit circuits.",
        status="uploaded",
    )
    test_session.add(syllabus)
    await test_session.commit()
    await test_session.refresh(syllabus)

    failing_llm = MockLLMProvider(
        extraction_data={},
        should_fail=True,
        error_msg="Rate limit exceeded: 429 Too Many Requests",
    )

    # Process pipeline and expect failure status to be recorded
    processed = await process_syllabus_pipeline(
        syllabus.id,
        db=test_session,
        provider=failing_llm,
    )

    assert processed.status == "failed"
    assert processed.error_message is not None
    assert "Rate limit exceeded" in processed.error_message

    # Verify GET /syllabi/{id}/skills returns failed status and message
    response = await client.get(
        f"/api/v1/syllabi/{syllabus.id}/skills",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["syllabus_id"] == str(syllabus.id)
    assert data["status"] == "failed"
    assert "Rate limit exceeded" in data["error_message"]
    assert data["total"] == 0
    assert data["skills"] == []


@pytest.mark.asyncio
async def test_syllabus_skills_isolation_and_not_found(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    inst_a = Institution(name="Univ A", city="City A")
    inst_b = Institution(name="Univ B", city="City B")
    test_session.add_all([inst_a, inst_b])
    await test_session.commit()
    await test_session.refresh(inst_a)
    await test_session.refresh(inst_b)

    user_a, token_a = await _create_test_user(
        test_session, "userA@univa.edu", institution_id=inst_a.id
    )
    user_b, token_b = await _create_test_user(
        test_session, "userB@univb.edu", institution_id=inst_b.id
    )

    syllabus_a = Syllabus(
        id=uuid.uuid4(),
        institution_id=inst_a.id,
        uploaded_by=user_a.id,
        title="Univ A Confidential Course",
        department="Engineering",
        filename="confidential.pdf",
        raw_text="Proprietary course text",
        status="ready",
    )
    test_session.add(syllabus_a)
    await test_session.commit()

    # User B should receive 404 when querying Univ A's syllabus skills
    res_b = await client.get(
        f"/api/v1/syllabi/{syllabus_a.id}/skills",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 404

    # Non-existent syllabus returns 404
    res_random = await client.get(
        f"/api/v1/syllabi/{uuid.uuid4()}/skills",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_random.status_code == 404

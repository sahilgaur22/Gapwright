"""End-to-End Pipeline Integration Test.

Validates the full workflow from academic ingestion to market gap analysis:
  1. Upload academic syllabus via API
  2. Process skills extraction & normalization pipeline (mocked LLM)
  3. Crawl industry vacancies via FixtureSource (offline curated dataset)
  4. Compute quantifiable gap analysis (covered vs missing vs obsolete)
  5. Generate curriculum modernization recommendations
  6. Export multi-format reports (CSV and PDF)
  7. Verify aggregated governance statistics in Policymaker Overview

Runs completely offline without external network or API keys.
"""

import hashlib
import io
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.db.base import Base
from app.db.models.user import Institution, User
from app.db.session import get_db
from app.main import app
from app.services.llm.base import LLMProvider
from app.services.skills.pipeline import process_syllabus_pipeline
from app.services.sources.seed import seed_job_sources


class DeterministicMockLLMProvider(LLMProvider):
    """Deterministic LLM Provider for CI/CD offline test pipelines."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    @property
    def provider_name(self) -> str:
        return "ci-mock"

    @property
    def model_name(self) -> str:
        return "ci-mock-model"

    async def extract_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        self.calls.append(prompt)
        prompt_lower = prompt.lower()
        sys_lower = (system_instruction or "").lower()

        # Recommendations response
        if (
            "curriculum design advisor" in sys_lower
            or "curriculum gap:" in prompt_lower
            or "skills_to_add" in prompt_lower
        ):
            return {
                "summary": (
                    "Curriculum provides sound programming foundations but lacks "
                    "production deep learning and cloud deployment tooling."
                ),
                "skills_to_add": [
                    {
                        "name": "PyTorch",
                        "category": "Frameworks",
                        "rationale": (
                            "High industry demand for deep learning frameworks in "
                            "data science vacancies."
                        ),
                        "suggested_module": "Module 5: Neural Networks & Deep Learning",
                        "suggested_weeks": 3,
                    },
                    {
                        "name": "Docker",
                        "category": "DevOps",
                        "rationale": (
                            "Essential standard for containerizing and deploying "
                            "analytical workloads."
                        ),
                        "suggested_module": (
                            "Module 6: Model Deployment & Containerization"
                        ),
                        "suggested_weeks": 2,
                    },
                ],
                "skills_to_drop": [
                    {
                        "name": "Git",
                        "category": "Tools",
                        "rationale": (
                            "Basic version control is assumed prerequisite rather "
                            "than core data science topic."
                        ),
                        "suggested_module": "Prune legacy scripting exercises",
                        "suggested_weeks": 1,
                    }
                ],
            }

        # Job posting skill extraction (e.g. Swiggy Lead Data Scientist)
        if "swiggy" in prompt_lower or "pricing and recommendation" in prompt_lower:
            return {
                "skills": [
                    {
                        "name": "Python",
                        "category": "Languages",
                        "evidence": "deep proficiency in Python",
                        "confidence": 0.98,
                    },
                    {
                        "name": "PyTorch",
                        "category": "Frameworks",
                        "evidence": "PyTorch, TensorFlow, Scikit-Learn",
                        "confidence": 0.95,
                    },
                    {
                        "name": "Docker",
                        "category": "DevOps",
                        "evidence": "model deployment on AWS with MLflow and Docker",
                        "confidence": 0.92,
                    },
                    {
                        "name": "SQL",
                        "category": "Databases",
                        "evidence": (
                            "Scikit-Learn, SQL, and distributed model deployment"
                        ),
                        "confidence": 0.90,
                    },
                ]
            }

        # Academic syllabus extraction response (CS 301)
        return {
            "skills": [
                {
                    "name": "Python",
                    "category": "Languages",
                    "evidence": (
                        "Python programming constructs, functions, and control flow"
                    ),
                    "confidence": 0.95,
                },
                {
                    "name": "SQL",
                    "category": "Databases",
                    "evidence": "Relational schema design and complex SQL queries",
                    "confidence": 0.92,
                },
                {
                    "name": "Git",
                    "category": "Tools",
                    "evidence": "Source code management using Git repositories",
                    "confidence": 0.88,
                },
            ]
        }

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        if isinstance(text, list):
            return [self._hash_vector(t) for t in text]
        return self._hash_vector(text)

    def _hash_vector(self, t: str) -> list[float]:
        digest = hashlib.md5(t.strip().lower().encode("utf-8")).hexdigest()
        idx = int(digest, 16) % 768
        vec = [0.0] * 768
        vec[idx] = 1.0
        return vec


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
async def test_full_pipeline_end_to_end(
    test_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Execute complete end-to-end integration pipeline from ingestion to governance."""
    mock_llm = DeterministicMockLLMProvider()

    # -------------------------------------------------------------------------
    # Setup: Create Institution and Users
    # -------------------------------------------------------------------------
    inst = Institution(
        id=uuid.uuid4(),
        name="National Technological Institute",
        city="Bengaluru",
    )
    admin = User(
        id=uuid.uuid4(),
        email="admin@nti.ac.in",
        password_hash="hashed_pw_test",
        role="admin",
        institution_id=inst.id,
    )
    educator = User(
        id=uuid.uuid4(),
        email="prof_sharma@nti.ac.in",
        password_hash="hashed_pw_test",
        role="educator",
        institution_id=inst.id,
    )
    policymaker = User(
        id=uuid.uuid4(),
        email="advisor@moe.gov.in",
        password_hash="hashed_pw_test",
        role="policymaker",
    )
    test_session.add_all([inst, admin, educator, policymaker])
    await test_session.commit()

    admin_token = create_access_token(subject=str(admin.id))
    educator_token = create_access_token(subject=str(educator.id))
    policymaker_token = create_access_token(subject=str(policymaker.id))

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=letter)
    c.drawString(100, 750, "CS 301: Foundations of Data Science")
    c.drawString(
        100,
        720,
        "Introduction to computational data analysis, Python programming, "
        "and relational databases.",
    )
    c.drawString(
        100, 690, "Unit 1: Python Programming Constructs and Data Manipulation"
    )
    c.drawString(100, 660, "Unit 2: Database Management & Relational SQL Queries")
    c.drawString(100, 630, "Unit 3: Distributed Version Control with Git and GitHub")
    c.save()
    pdf_bytes = pdf_buf.getvalue()

    upload_resp = await client.post(
        "/api/v1/syllabi",
        data={
            "title": "CS 301: Foundations of Data Science",
            "department": "Computer Science & Engineering",
        },
        files={"file": ("cs301_syllabus.pdf", pdf_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {educator_token}"},
    )

    assert upload_resp.status_code == 201
    syl_data = upload_resp.json()
    syllabus_id = syl_data["id"]
    assert syl_data["title"] == "CS 301: Foundations of Data Science"
    assert syl_data["status"] == "uploaded"

    # -------------------------------------------------------------------------
    # Step 2: Process Syllabus Skills Pipeline (Mocked LLM)
    # -------------------------------------------------------------------------
    processed_syllabus = await process_syllabus_pipeline(
        uuid.UUID(syllabus_id),
        db=test_session,
        provider=mock_llm,
    )
    assert processed_syllabus.status == "ready"

    # Query skills endpoint
    skills_resp = await client.get(
        f"/api/v1/syllabi/{syllabus_id}/skills",
        headers={"Authorization": f"Bearer {educator_token}"},
    )
    assert skills_resp.status_code == 200
    skills_body = skills_resp.json()
    extracted_names = [s["canonical_name"] for s in skills_body["skills"]]
    assert "Python" in extracted_names
    assert "SQL" in extracted_names
    assert "Git" in extracted_names

    # -------------------------------------------------------------------------
    # Step 3: Crawl Market Postings via FixtureSource
    # -------------------------------------------------------------------------
    with patch(
        "app.api.v1.jobs.get_llm_provider",
        return_value=mock_llm,
    ):
        crawl_resp = await client.post(
            "/api/v1/jobs/crawl",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "sources": ["fixture"],
                "pairs": [{"role": "Data Scientist", "location": "Bangalore"}],
                "extract_skills": True,
            },
        )

    assert crawl_resp.status_code == 200
    crawl_result = crawl_resp.json()
    assert crawl_result["status"] == "completed"
    assert crawl_result["jobs_persisted"] > 0

    # Verify jobs query returns persisted vacancies
    jobs_resp = await client.get("/api/v1/jobs?role=Data+Scientist")
    assert jobs_resp.status_code == 200
    jobs_body = jobs_resp.json()
    assert jobs_body["total"] > 0

    # -------------------------------------------------------------------------
    # Step 4: Compute Quantifiable Gap Analysis
    # -------------------------------------------------------------------------
    analysis_resp = await client.post(
        "/api/v1/analysis",
        json={
            "syllabus_id": syllabus_id,
            "role_query": "Data Scientist",
            "location": "Bangalore",
        },
    )
    assert analysis_resp.status_code == 201
    analysis_data = analysis_resp.json()
    analysis_id = analysis_data["id"]

    assert analysis_data["role_query"] == "Data Scientist"
    assert "gap_pct" in analysis_data
    assert "coverage_pct" in analysis_data
    assert analysis_data["gap_pct"] + analysis_data["coverage_pct"] == pytest.approx(
        100.0, abs=0.5
    )

    # Inspect categorized skills: covered vs missing
    analysis_items = analysis_data["items"]
    covered_skills = [
        item["skill_name"] for item in analysis_items if item["kind"] == "covered"
    ]
    missing_skills = [
        item["skill_name"] for item in analysis_items if item["kind"] == "missing"
    ]

    # Python is in syllabus and in Data Scientist requirements -> Covered
    assert "Python" in covered_skills
    # PyTorch or Docker is in market requirements but not in CS 301 -> Missing
    assert len(missing_skills) > 0

    # -------------------------------------------------------------------------
    # Step 5: Generate Curriculum Modernization Recommendations
    # -------------------------------------------------------------------------
    with patch(
        "app.api.v1.analysis.get_llm_provider",
        return_value=mock_llm,
    ):
        recs_resp = await client.get(f"/api/v1/analysis/{analysis_id}/recommendations")

    assert recs_resp.status_code == 200
    recs_data = recs_resp.json()
    assert len(recs_data["skills_to_add"]) > 0
    first_add = recs_data["skills_to_add"][0]
    assert "skill_name" in first_add
    assert "suggested_module" in first_add
    assert "suggested_weeks" in first_add
    assert len(recs_data["summary"]) > 20

    # -------------------------------------------------------------------------
    # Step 6: Export Multi-Format Compliance Reports
    # -------------------------------------------------------------------------
    # CSV Export
    csv_resp = await client.get(f"/api/v1/reports/{analysis_id}/export?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert "Python" in csv_resp.text
    assert "Covered" in csv_resp.text

    # PDF Export
    with patch(
        "app.api.v1.reports.get_llm_provider",
        return_value=mock_llm,
    ):
        pdf_resp = await client.get(f"/api/v1/reports/{analysis_id}/export?format=pdf")
    assert pdf_resp.status_code == 200
    assert "application/pdf" in pdf_resp.headers["content-type"]
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 1000

    # -------------------------------------------------------------------------
    # Step 7: Verify Governance Analytics in Policymaker Overview
    # -------------------------------------------------------------------------
    # Student / Educator without privileges should be rejected
    unauth_policy_resp = await client.get(
        "/api/v1/policy/overview",
        headers={"Authorization": f"Bearer {educator_token}"},
    )
    assert unauth_policy_resp.status_code == 403

    # Authorized Policymaker should receive aggregated cross-curriculum metrics
    policy_resp = await client.get(
        "/api/v1/policy/overview",
        headers={"Authorization": f"Bearer {policymaker_token}"},
    )
    assert policy_resp.status_code == 200
    policy_summary = policy_resp.json()

    assert policy_summary["total_analyses"] >= 1
    assert policy_summary["total_institutions"] >= 1
    assert "average_gap_pct" in policy_summary
    assert "average_coverage_pct" in policy_summary
    assert len(policy_summary["institutions"]) >= 1
    assert (
        policy_summary["institutions"][0]["institution"]
        == "National Technological Institute"
    )

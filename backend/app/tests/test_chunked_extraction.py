from typing import Any

import pytest

from app.schemas.skill import SkillExtractionItem
from app.services.llm.base import LLMProvider
from app.services.skills.chunking import SectionChunker
from app.services.skills.extractor import extract_skills_from_document
from app.services.skills.merger import merge_and_deduplicate_skills


class DynamicMockLLMProvider:
    """Mock LLMProvider inspecting prompt content to generate matching skills."""

    def __init__(self) -> None:
        self.call_count = 0
        self.chunks_received: list[str] = []

    @property
    def provider_name(self) -> str:
        return "dynamic-mock"

    @property
    def model_name(self) -> str:
        return "dynamic-mock-model"

    async def extract_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        self.call_count += 1
        self.chunks_received.append(prompt)

        # Detect tech keywords in prompt and return skills
        skills: list[dict[str, Any]] = []
        lower_prompt = prompt.lower()

        if "python" in lower_prompt:
            skills.append(
                {
                    "name": "Python",
                    "category": "Languages",
                    "evidence": f"Python mentioned in chunk {self.call_count}",
                    "confidence": 0.95,
                }
            )
        if "docker" in lower_prompt:
            skills.append(
                {
                    "name": "Docker",
                    "category": "Cloud & DevOps",
                    "evidence": f"Docker containerization in chunk {self.call_count}",
                    "confidence": 0.90,
                }
            )
        if "kubernetes" in lower_prompt or "k8s" in lower_prompt:
            skills.append(
                {
                    "name": "Kubernetes",
                    "category": "Cloud & DevOps",
                    "evidence": f"Kubernetes in chunk {self.call_count}",
                    "confidence": 0.92,
                }
            )
        if "postgresql" in lower_prompt:
            skills.append(
                {
                    "name": "PostgreSQL",
                    "category": "Databases",
                    "evidence": f"PostgreSQL queries in chunk {self.call_count}",
                    "confidence": 0.88,
                }
            )
        if "pytorch" in lower_prompt:
            skills.append(
                {
                    "name": "PyTorch",
                    "category": "Machine Learning",
                    "evidence": f"PyTorch deep neural nets in chunk {self.call_count}",
                    "confidence": 0.97,
                }
            )
        if "fastapi" in lower_prompt:
            skills.append(
                {
                    "name": "FastAPI",
                    "category": "Frameworks",
                    "evidence": f"FastAPI microservices in chunk {self.call_count}",
                    "confidence": 0.91,
                }
            )

        return {"skills": skills}

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        return [0.1, 0.2, 0.3]


def _generate_30_page_syllabus() -> str:
    """Generate a realistic 30-page equivalent curriculum syllabus document

    spanning 15 distinct modules with extensive text and recurring skills.
    """
    sections: list[str] = [
        "# CS 500: Advanced Distributed Systems & Cloud Architecture\n"
        "## COURSE DESCRIPTION\n"
        "This comprehensive graduate-level course provides an exploration "
        "of modern software architecture, cloud platforms, and data infrastructure. "
        "Students will build robust backend applications using Python, containerize "
        "with Docker, and manage distributed workloads using Kubernetes.",
        "## PREREQUISITES\n"
        "Proficiency in Python programming, relational databases (PostgreSQL), and "
        "basic command-line operations.",
    ]

    modules_data = [
        (
            "Module 1: Concurrency and Threading",
            "Deep dive into async I/O, threads, and Python multiprocessing.",
        ),
        (
            "Module 2: Web APIs with FastAPI",
            "Designing high-performance REST APIs with FastAPI and Pydantic.",
        ),
        (
            "Module 3: Database Internals",
            "Indexing, transaction isolation, and query tuning in PostgreSQL.",
        ),
        (
            "Module 4: Containerization Basics",
            "Building production-grade Docker images and multi-stage builds.",
        ),
        (
            "Module 5: Cluster Orchestration",
            "Pods, Services, and Ingress routing in Kubernetes.",
        ),
        (
            "Module 6: Microservices Communication",
            "Message brokers and event-driven architectures with Python.",
        ),
        (
            "Module 7: Infrastructure Automation",
            "Automated deployment of Docker containers to cloud clusters.",
        ),
        (
            "Module 8: Deep Learning Systems",
            "Deploying PyTorch models as containerized microservices.",
        ),
        (
            "Module 9: High-Throughput Data Ingestion",
            "Scaling PostgreSQL and stream processing in Python.",
        ),
        (
            "Module 10: Production Observability",
            "Logging, tracing, and health checks for Kubernetes workloads.",
        ),
        (
            "Module 11: Machine Learning Pipelines",
            "Training pipelines with PyTorch and distributed workers.",
        ),
        (
            "Module 12: Continuous Delivery",
            "Automating testing and deployment pipelines for Docker images.",
        ),
        (
            "Module 13: Distributed Consensus",
            "Raft consensus protocol implementation in Python.",
        ),
        (
            "Module 14: Cloud Security",
            "Role-based access control and secrets management in Kubernetes.",
        ),
        (
            "Module 15: Capstone System Project",
            "End-to-end scalable application with FastAPI, PostgreSQL, Docker, K8s.",
        ),
    ]

    for title, description in modules_data:
        padding = (
            "Each module requires weekly laboratory assignments and reading "
            "seminal research papers. Students will submit pull requests and pass "
            "automated continuous integration testing. Performance metrics and latency "
            "benchmarks must be documented thoroughly in the report.\n"
        ) * 5
        sections.append(f"### {title}\n{description}\n\n{padding}")

    return "\n\n".join(sections)


def test_section_chunker_splits_headings() -> None:
    text = (
        "# Title\nIntro text\n\n"
        "## Module 1: Basics\nContent for module 1\n\n"
        "## Module 2: Advanced\nContent for module 2"
    )
    sections = SectionChunker.split_into_sections(text)
    assert len(sections) == 3
    assert "Module 1" in sections[1][0]
    assert "Content for module 1" in sections[1][1]


def test_merge_and_deduplicate_skills() -> None:
    raw_skills = [
        SkillExtractionItem(
            name="python",
            category="Programming",
            evidence="Python used in Week 1",
            confidence=0.85,
        ),
        SkillExtractionItem(
            name="Python",
            category="Languages",
            evidence="Advanced Python programming in Week 4",
            confidence=0.98,
        ),
        SkillExtractionItem(
            name="Docker",
            category="DevOps",
            evidence="Docker in Lab 1",
            confidence=0.90,
        ),
        SkillExtractionItem(
            name="docker",
            category="Cloud",
            evidence="Docker deployment in Lab 5",
            confidence=0.88,
        ),
    ]

    merged = merge_and_deduplicate_skills(raw_skills)
    assert len(merged) == 2

    python_skill = next(s for s in merged if s.name == "Python")
    assert python_skill.confidence == 0.98
    assert python_skill.category == "Languages"
    assert "Week 1" in python_skill.evidence
    assert "Week 4" in python_skill.evidence
    assert " | " in python_skill.evidence

    docker_skill = next(s for s in merged if s.name == "Docker")
    assert docker_skill.confidence == 0.90


@pytest.mark.asyncio
async def test_30_page_fixture_yields_deduped_skills() -> None:
    syllabus_text = _generate_30_page_syllabus()
    assert len(syllabus_text.split()) > 2000

    provider = DynamicMockLLMProvider()
    assert isinstance(provider, LLMProvider)

    # Process long document with section-aware chunking
    result = await extract_skills_from_document(
        syllabus_text,
        provider,
        max_chunk_tokens=500,  # Forces multi-chunk splitting across modules
        overlap_tokens=50,
    )

    # Verify multiple chunks were generated and processed
    assert provider.call_count >= 5

    # Verify skill deduplication
    assert len(result.skills) > 0
    names = [s.name for s in result.skills]
    # No duplicate skill names (case-insensitive)
    assert len(names) == len(set(n.lower() for n in names))

    # Core recurring skills must be present
    assert "Python" in names
    assert "Docker" in names
    assert "Kubernetes" in names
    assert "PostgreSQL" in names
    assert "FastAPI" in names
    assert "PyTorch" in names

    # Verify that evidence from multiple chunks was merged
    python_skill = next(s for s in result.skills if s.name == "Python")
    assert " | " in python_skill.evidence

    docker_skill = next(s for s in result.skills if s.name == "Docker")
    assert " | " in docker_skill.evidence

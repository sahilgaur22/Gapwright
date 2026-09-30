import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.skill import SkillExtractionItem, SkillExtractionResult
from app.services.llm.base import LLMProvider
from app.services.llm.exceptions import ModelResponseError
from app.services.llm.prompts import (
    PROMPT_VERSION_SKILL_EXTRACTION,
    SKILL_EXTRACTION_USER_TEMPLATE,
    SKILL_REPAIR_USER_TEMPLATE,
)
from app.services.skills.extractor import extract_skills_from_text


class MockLLMProvider:
    """Mock LLMProvider for testing skill extraction with recorded responses."""

    def __init__(self, responses: list[dict[str, Any] | list[Any]]) -> None:
        self.responses = responses
        self.call_count = 0
        self.prompts_received: list[str] = []

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
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> dict[str, Any] | list[Any]:
        self.prompts_received.append(prompt)
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        raise RuntimeError("No more mock responses configured")

    async def embed(
        self,
        text: str | list[str],
        *,
        max_retries: int = 3,
    ) -> list[float] | list[list[float]]:
        return [0.1, 0.2, 0.3]


def _load_golden_file() -> dict[str, Any]:
    golden_path = Path(__file__).parent / "fixtures" / "golden_skills_response.json"
    with open(golden_path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def test_prompt_version_and_template_formatting() -> None:
    assert PROMPT_VERSION_SKILL_EXTRACTION == "v1.0.0"
    user_p = SKILL_EXTRACTION_USER_TEMPLATE.format(text="Sample Course Syllabus")
    assert "Sample Course Syllabus" in user_p

    repair_p = SKILL_REPAIR_USER_TEMPLATE.format(
        errors="Field 'evidence' missing",
        raw_output='{"skills": [{"name": "Python"}]}',
    )
    assert "Field 'evidence' missing" in repair_p
    assert "Python" in repair_p


def test_skill_schema_validation() -> None:
    # Valid item
    item = SkillExtractionItem(
        name="Kubernetes",
        category="Cloud & DevOps",
        evidence="Deploy services to a Kubernetes cluster.",
        confidence=0.95,
    )
    assert item.name == "Kubernetes"
    assert item.confidence == 0.95

    # Container validation
    result = SkillExtractionResult(skills=[item])
    assert len(result.skills) == 1

    # Invalid confidence (> 1.0)
    with pytest.raises(ValidationError):
        SkillExtractionItem(
            name="Kubernetes",
            category="Cloud",
            evidence="Deploy services",
            confidence=1.5,
        )

    # Missing required field
    with pytest.raises(ValidationError):
        SkillExtractionItem.model_validate(
            {"name": "Python", "category": "Languages"}
        )


@pytest.mark.asyncio
async def test_extract_skills_from_golden_response() -> None:
    golden_data = _load_golden_file()
    mock_provider = MockLLMProvider(responses=[golden_data])
    assert isinstance(mock_provider, LLMProvider)

    syllabus_sample = (
        "CS 482: Deep Learning. Hands-on model development will use PyTorch "
        "for tensor operations and backpropagation. Week 6 analyzes self-attention "
        "mechanisms and Transformer architecture. All lab assignments must be "
        "containerized and run inside Docker containers."
    )

    result = await extract_skills_from_text(syllabus_sample, mock_provider)

    assert len(result.skills) == 3
    names = [s.name for s in result.skills]
    assert "PyTorch" in names
    assert "Transformer Architecture" in names
    assert "Docker" in names

    pytorch = next(s for s in result.skills if s.name == "PyTorch")
    assert pytorch.category == "Machine Learning"
    assert "PyTorch for tensor operations" in pytorch.evidence
    assert pytorch.confidence == 0.98
    assert mock_provider.call_count == 1


@pytest.mark.asyncio
async def test_extract_skills_repair_retry_success() -> None:
    # First response is malformed (missing 'evidence' field)
    malformed_response = {
        "skills": [
            {"name": "Rust", "category": "Languages", "confidence": 0.9}
        ]
    }
    # Second response is repaired and valid
    repaired_response = {
        "skills": [
            {
                "name": "Rust",
                "category": "Languages",
                "evidence": "Students will build concurrency modules in Rust.",
                "confidence": 0.95,
            }
        ]
    }

    mock_provider = MockLLMProvider(responses=[malformed_response, repaired_response])
    result = await extract_skills_from_text("Rust concurrency course", mock_provider)

    assert len(result.skills) == 1
    assert result.skills[0].name == "Rust"
    assert "concurrency modules in Rust" in result.skills[0].evidence
    assert mock_provider.call_count == 2
    assert "repair" in mock_provider.prompts_received[1].lower()


@pytest.mark.asyncio
async def test_extract_skills_repair_exhausted_raises_error() -> None:
    # Both initial and repair responses are malformed
    bad_resp_1 = {"skills": [{"name": "OnlyName"}]}
    bad_resp_2 = {"skills": [{"name": "StillOnlyName"}]}

    mock_provider = MockLLMProvider(responses=[bad_resp_1, bad_resp_2])

    with pytest.raises(ModelResponseError, match="failed schema validation"):
        await extract_skills_from_text(
            "Invalid text", mock_provider, max_repair_retries=1
        )

    assert mock_provider.call_count == 2


@pytest.mark.asyncio
async def test_extract_skills_empty_text() -> None:
    mock_provider = MockLLMProvider(responses=[])
    result = await extract_skills_from_text("   \n   ", mock_provider)
    assert result.skills == []
    assert mock_provider.call_count == 0

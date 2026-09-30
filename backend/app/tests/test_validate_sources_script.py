from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.services.sources.base import BaseJobSource
from app.services.sources.models import RawJob
from scripts.validate_sources import (
    compute_metrics,
    format_table,
    run_validation,
    validate_source,
)


class DummyTestSource(BaseJobSource):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def priority(self) -> int:
        return 1

    async def search(
        self,
        role: str,
        location: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[RawJob]:
        return []


def test_compute_metrics_with_sample_jobs() -> None:
    source = DummyTestSource()
    jobs = [
        RawJob(
            source="dummy",
            external_id="1",
            title="Software Engineer",
            company="Acme",
            location="Bangalore",
            description="Short desc",  # len 10
            description_is_truncated=False,
            posted_at=datetime(2026, 9, 28, 10, 0, tzinfo=UTC),
        ),
        RawJob(
            source="dummy",
            external_id="2",
            title="Senior Developer",
            company="Globex",
            location="Bangalore",
            description="Much longer job description text",  # len 32
            description_is_truncated=True,
            posted_at=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
        ),
    ]

    res = compute_metrics(source, jobs)
    assert res.status == "OK"
    assert res.result_count == 2
    assert res.newest_posted_at == datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    assert res.oldest_posted_at == datetime(2026, 9, 28, 10, 0, tzinfo=UTC)
    assert res.median_desc_length == 21.0  # (10 + 32) / 2
    assert res.pct_truncated == 50.0  # 1 out of 2
    assert len(res.sample_titles) == 2


def test_compute_metrics_empty() -> None:
    source = DummyTestSource()
    res = compute_metrics(source, [])
    assert res.status == "EMPTY"
    assert res.result_count == 0


def test_compute_metrics_error() -> None:
    source = DummyTestSource()
    res = compute_metrics(source, [], error_msg="Connection timed out")
    assert res.status == "ERROR"
    assert res.error_message == "Connection timed out"


def test_format_table_renders_properly() -> None:
    source = DummyTestSource()
    jobs = [
        RawJob(
            source="dummy",
            external_id="1",
            title="Cloud Architect",
            description="Design cloud systems",
            posted_at=datetime(2026, 9, 28, 10, 0, tzinfo=UTC),
        )
    ]
    res = compute_metrics(source, jobs)
    table_str = format_table([res])

    assert "dummy" in table_str
    assert "P1" in table_str
    assert "OK" in table_str
    assert "Cloud Architect" in table_str


@pytest.mark.asyncio
async def test_validate_source_handles_exceptions() -> None:
    mock_source = AsyncMock(spec=BaseJobSource)
    mock_source.name = "failing_source"
    mock_source.priority = 1
    mock_source.search.side_effect = RuntimeError("API service offline")

    res = await validate_source(mock_source, role="DevOps", location="Pune", limit=5)
    assert res.status == "ERROR"
    assert "API service offline" in (res.error_message or "")


@pytest.mark.asyncio
async def test_run_validation_against_fixture_source() -> None:
    results, success = await run_validation(
        source_names=["fixture"],
        role="Data Scientist",
        location="Bangalore",
        limit=5,
        require_p1=False,
    )
    assert len(results) == 1
    assert results[0].source_name == "fixture"
    assert results[0].status == "OK"
    assert results[0].result_count >= 1
    assert success is True

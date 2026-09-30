"""Job source validation script for Gapwright.

Executes a live or test query against enabled job source connectors and reports:
- HTTP / execution status
- Posting count returned
- Newest and oldest posted_at dates
- Median description character length
- Percentage of descriptions truncated
- Sample job titles

Exits non-zero if a P1 source returns 0 recent results when require_p1 is on.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Ensure backend root is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.sources import source_registry  # noqa: E402
from app.services.sources.base import BaseJobSource  # noqa: E402
from app.services.sources.models import RawJob  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("validate_sources")


@dataclass
class SourceValidationResult:
    source_name: str
    priority: int
    status: str  # "OK", "EMPTY", "ERROR", "DISABLED"
    result_count: int = 0
    newest_posted_at: datetime | None = None
    oldest_posted_at: datetime | None = None
    median_desc_length: float = 0.0
    pct_truncated: float = 0.0
    sample_titles: list[str] = field(default_factory=list)
    error_message: str | None = None


def compute_metrics(
    source: BaseJobSource,
    jobs: list[RawJob],
    error_msg: str | None = None,
) -> SourceValidationResult:
    """Compute summary statistics for a set of raw job results from a source."""
    if error_msg:
        return SourceValidationResult(
            source_name=source.name,
            priority=source.priority,
            status="ERROR",
            error_message=error_msg,
        )

    if not jobs:
        return SourceValidationResult(
            source_name=source.name,
            priority=source.priority,
            status="EMPTY",
        )

    posted_dates = [j.posted_at for j in jobs if j.posted_at is not None]
    newest = max(posted_dates) if posted_dates else None
    oldest = min(posted_dates) if posted_dates else None

    lengths = [len(j.description) for j in jobs]
    median_len = float(statistics.median(lengths)) if lengths else 0.0

    trunc_count = sum(1 for j in jobs if j.description_is_truncated)
    pct_trunc = (trunc_count / len(jobs)) * 100.0 if jobs else 0.0

    sample_titles = [j.title for j in jobs[:3]]

    return SourceValidationResult(
        source_name=source.name,
        priority=source.priority,
        status="OK",
        result_count=len(jobs),
        newest_posted_at=newest,
        oldest_posted_at=oldest,
        median_desc_length=median_len,
        pct_truncated=pct_trunc,
        sample_titles=sample_titles,
    )


async def validate_source(
    source: BaseJobSource,
    role: str,
    location: str | None,
    limit: int,
) -> SourceValidationResult:
    """Execute a query against a single source connector and compute metrics."""
    try:
        # P2 remote sources typically don't accept Indian city locations
        loc = location if source.priority == 1 or source.name == "fixture" else None
        jobs = await source.search(role=role, location=loc, limit=limit)
        return compute_metrics(source, jobs)
    except Exception as exc:
        logger.error(f"Error querying source {source.name}: {exc}")
        return compute_metrics(source, [], error_msg=str(exc))


async def run_validation(
    source_names: Sequence[str] | None = None,
    role: str = "Data Scientist",
    location: str | None = "Bangalore",
    limit: int = 10,
    require_p1: bool = True,
) -> tuple[list[SourceValidationResult], bool]:
    """Run validation across specified or configured sources.

    Returns:
        (results, is_successful)
    """
    if source_names:
        selected_sources: list[BaseJobSource] = []
        for name in source_names:
            src = source_registry.get_source(name)
            if src:
                selected_sources.append(src)
            else:
                logger.warning(f"Source '{name}' not found in registry")
    else:
        configured = settings.ENABLED_SOURCES or "fixture"
        names = [s.strip().lower() for s in configured.split(",") if s.strip()]
        selected_sources = []
        for n in names:
            src = source_registry.get_source(n)
            if src is not None:
                selected_sources.append(src)

    if not selected_sources:
        print("No sources selected for validation.")
        return [], False

    tasks = [
        validate_source(src, role=role, location=location, limit=limit)
        for src in selected_sources
    ]
    results = await asyncio.gather(*tasks)

    # Check P1 source success
    overall_success = True
    for res in results:
        if (
            require_p1
            and res.priority == 1
            and (res.status != "OK" or res.result_count == 0)
        ):
            overall_success = False

    return results, overall_success


def format_table(results: list[SourceValidationResult]) -> str:
    """Format validation results into a human-readable table."""
    header = (
        f"{'Source':<10} | {'Tier':<4} | {'Status':<6} | "
        f"{'Count':<5} | {'Median Len':<10} | {'% Trunc':<7} | {'Sample Titles':<32}"
    )
    lines: list[str] = [
        "=" * 86,
        header,
        "-" * 86,
    ]

    for r in results:
        tier = f"P{r.priority}"
        count_str = str(r.result_count)
        med_len = f"{int(r.median_desc_length)} chars" if r.result_count > 0 else "-"
        trunc_str = f"{r.pct_truncated:.1f}%" if r.result_count > 0 else "-"
        titles = ", ".join(r.sample_titles)[:32] if r.sample_titles else "-"
        if r.status == "ERROR":
            titles = f"Error: {r.error_message or 'Unknown'}"[:32]

        row = (
            f"{r.source_name:<10} | {tier:<4} | {r.status:<6} | "
            f"{count_str:<5} | {med_len:<10} | {trunc_str:<7} | {titles:<32}"
        )
        lines.append(row)

    lines.append("=" * 86)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Gapwright job data source connectors."
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=None,
        help="Comma-separated source names (e.g. 'adzuna,jooble,fixture')",
    )
    parser.add_argument(
        "--role",
        type=str,
        default="Data Scientist",
        help="Target job role query (default: 'Data Scientist')",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="Bangalore",
        help="Target location (default: 'Bangalore')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum jobs per source query (default: 10)",
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Validate only the offline curated fixture source",
    )
    parser.add_argument(
        "--no-require-p1",
        action="store_true",
        help="Do not exit non-zero if P1 sources return 0 items",
    )

    args = parser.parse_args()

    if args.fixture_only:
        sources_to_run = ["fixture"]
        require_p1 = False
    elif args.sources:
        sources_to_run = [
            s.strip().lower() for s in args.sources.split(",") if s.strip()
        ]
        require_p1 = not args.no_require_p1
    else:
        sources_to_run = None
        require_p1 = not args.no_require_p1

    print("\nStarting Gapwright Job Source Validation...")
    print(f"Role: '{args.role}' | Location: '{args.location}' | Limit: {args.limit}\n")

    results, success = asyncio.run(
        run_validation(
            source_names=sources_to_run,
            role=args.role,
            location=args.location,
            limit=args.limit,
            require_p1=require_p1,
        )
    )

    print(format_table(results))

    if not success and require_p1:
        print(
            "\n[VALIDATION FAILED] One or more P1 sources returned 0 results or failed."
        )
        sys.exit(1)
    else:
        print("\n[VALIDATION SUCCESS] Enabled sources validated successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()

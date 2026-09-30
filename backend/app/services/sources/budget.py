import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import ApiUsage

logger = logging.getLogger(__name__)


class BudgetExhaustedError(Exception):
    """Raised when an operation would exceed the configured daily API call budget."""

    def __init__(self, source: str, limit: int, current: int) -> None:
        self.source = source
        self.limit = limit
        self.current = current
        super().__init__(
            f"Daily budget exhausted for source '{source}': "
            f"used {current}/{limit} calls"
        )


async def get_daily_usage(
    db: AsyncSession,
    source_name: str,
    target_date: date | None = None,
) -> int:
    """Retrieve total API calls used by a source on given date (defaults to today)."""
    d = target_date or date.today()
    query = select(ApiUsage.calls).where(
        ApiUsage.source == source_name,
        ApiUsage.day == d,
    )
    result = await db.execute(query)
    current_calls = result.scalar_one_or_none()
    return int(current_calls) if current_calls is not None else 0


async def check_budget(
    db: AsyncSession,
    source_name: str,
    limit: int,
    requested_calls: int = 1,
    target_date: date | None = None,
) -> bool:
    """Return True if requested calls do not exceed the remaining daily budget."""
    if limit <= 0:
        return False
    current = await get_daily_usage(db, source_name, target_date)
    return (current + requested_calls) <= limit


async def get_remaining_budget(
    db: AsyncSession,
    source_name: str,
    limit: int,
    target_date: date | None = None,
) -> int:
    """Return number of calls remaining for today (at least 0)."""
    current = await get_daily_usage(db, source_name, target_date)
    return max(0, limit - current)


async def record_usage(
    db: AsyncSession,
    source_name: str,
    calls: int = 1,
    target_date: date | None = None,
) -> int:
    """Increment call count for the specified source and date, persisting changes."""
    d = target_date or date.today()
    query = select(ApiUsage).where(
        ApiUsage.source == source_name,
        ApiUsage.day == d,
    )
    result = await db.execute(query)
    usage = result.scalar_one_or_none()

    if usage is None:
        usage = ApiUsage(source=source_name, day=d, calls=calls)
        db.add(usage)
    else:
        usage.calls += calls
        db.add(usage)

    await db.commit()
    await db.refresh(usage)
    return usage.calls

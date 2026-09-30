import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.job import CrawlState

logger = logging.getLogger(__name__)


async def get_crawl_state(
    db: AsyncSession,
    source: str,
    role_query: str,
    location: str,
) -> CrawlState | None:
    """Retrieve the persistent incremental crawl state for a source and query."""
    src = source.lower().strip()
    rq = role_query.lower().strip()
    loc = location.lower().strip()

    stmt = select(CrawlState).where(
        CrawlState.source == src,
        CrawlState.role_query == rq,
        CrawlState.location == loc,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_crawl_state(
    db: AsyncSession,
    source: str,
    role_query: str,
    location: str,
    newest_posted_at: datetime | None = None,
    cursor: str | None = None,
) -> CrawlState:
    """Create or update incremental crawl state with latest execution timestamps."""
    src = source.lower().strip()
    rq = role_query.lower().strip()
    loc = location.lower().strip()
    now = datetime.now(UTC)

    state = await get_crawl_state(db, src, rq, loc)
    if state is None:
        state = CrawlState(
            source=src,
            role_query=rq,
            location=loc,
            last_run_at=now,
            newest_posted_at=newest_posted_at,
            cursor=cursor,
        )
        db.add(state)
    else:
        if newest_posted_at and (
            state.newest_posted_at is None
            or newest_posted_at > state.newest_posted_at
        ):
            state.newest_posted_at = newest_posted_at
        if cursor is not None:
            state.cursor = cursor

    await db.flush()
    return state

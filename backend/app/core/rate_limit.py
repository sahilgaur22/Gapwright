import time
from collections import defaultdict
from collections.abc import Callable
from typing import ClassVar

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Thread-safe in-memory sliding window rate limiter per client IP."""

    _instances: ClassVar[dict[str, "InMemoryRateLimiter"]] = {}

    def __init__(self, times: int, seconds: int, name: str = "default") -> None:
        self.times = times
        self.seconds = seconds
        self.name = name
        self._history: dict[str, list[float]] = defaultdict(list)

    @classmethod
    def get(cls, times: int, seconds: int, name: str) -> "InMemoryRateLimiter":
        key = f"{name}:{times}:{seconds}"
        if key not in cls._instances:
            cls._instances[key] = cls(times=times, seconds=seconds, name=name)
        return cls._instances[key]

    def is_rate_limited(self, client_id: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.seconds
        window = [ts for ts in self._history[client_id] if ts > cutoff]

        if len(window) >= self.times:
            retry_after = int(self.seconds - (now - window[0])) + 1
            self._history[client_id] = window
            return True, max(1, retry_after)

        window.append(now)
        self._history[client_id] = window
        return False, 0


def rate_limit(times: int, seconds: int = 60, name: str = "rate_limit") -> Callable:
    """FastAPI dependency for endpoint rate limiting by client IP."""
    limiter = InMemoryRateLimiter.get(times=times, seconds=seconds, name=name)

    async def dependency(request: Request) -> None:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        limited, retry_after = limiter.is_rate_limited(client_ip)
        if limited:
            detail_msg = (
                f"Rate limit exceeded for {name}. Please wait {retry_after} seconds."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail_msg,
                headers={"Retry-After": str(retry_after)},
            )

    return dependency

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_update: float = field(default_factory=time.monotonic)
    last_request_time: float = 0.0

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)

    def can_consume(self, count: float = 1.0) -> bool:
        self.refill()
        return self.tokens >= count

    def consume(self, count: float = 1.0) -> bool:
        self.refill()
        if self.tokens >= count:
            self.tokens -= count
            self.last_request_time = time.monotonic()
            return True
        return False


class DomainRateLimiter:
    """In-memory rate limiter enforcing per-domain token buckets and politeness."""

    def __init__(
        self,
        default_capacity: float = 10.0,
        default_refill_rate: float = 2.0,  # 2 requests/sec
    ) -> None:
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: dict[str, TokenBucket] = {}
        self._politeness_delays: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def set_rule(
        self,
        domain: str,
        *,
        capacity: float,
        refill_rate: float,
        min_delay_seconds: float = 0.0,
    ) -> None:
        """Configure bucket capacity, refill rate, and politeness delay for a domain."""
        self._buckets[domain] = TokenBucket(capacity=capacity, refill_rate=refill_rate)
        if min_delay_seconds > 0:
            self._politeness_delays[domain] = min_delay_seconds

    def _get_bucket(self, domain: str) -> TokenBucket:
        if domain not in self._buckets:
            self._buckets[domain] = TokenBucket(
                capacity=self.default_capacity,
                refill_rate=self.default_refill_rate,
            )
        return self._buckets[domain]

    async def acquire(
        self,
        domain: str,
        tokens: float = 1.0,
        timeout: float = 10.0,
    ) -> bool:
        """Acquire tokens for a domain, honoring minimum politeness delays.

        Returns True if acquired, False if timed out.
        """
        start_time = time.monotonic()
        while True:
            async with self._lock:
                bucket = self._get_bucket(domain)
                politeness = self._politeness_delays.get(domain, 0.0)
                now = time.monotonic()

                # Check politeness delay since last request
                elapsed_since_last = now - bucket.last_request_time
                if bucket.last_request_time > 0 and elapsed_since_last < politeness:
                    sleep_needed = politeness - elapsed_since_last
                else:
                    sleep_needed = 0.0

                if sleep_needed == 0.0 and bucket.consume(tokens):
                    return True

            if timeout is not None and (time.monotonic() - start_time) >= timeout:
                return False

            sleep_duration = max(0.05, sleep_needed)
            await asyncio.sleep(sleep_duration)


# Global default limiter instance
rate_limiter = DomainRateLimiter()

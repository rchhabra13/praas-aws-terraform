"""Token-bucket rate limiter for throttling per-client request rates."""
import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Simple in-memory token-bucket rate limiter.

    Each client gets `capacity` tokens that refill at `refill_rate` tokens/sec.
    A request costs 1 token; requests are rejected when the bucket is empty.
    """

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: dict[str, _Bucket] = {}

    def _get_bucket(self, client_id: str) -> _Bucket:
        bucket = self._buckets.get(client_id)
        if bucket is None:
            bucket = _Bucket(tokens=self.capacity, last_refill=time.monotonic())
            self._buckets[client_id] = bucket
        return bucket

    def allow(self, client_id: str) -> bool:
        """Return True and consume a token if the client is under its rate limit."""
        bucket = self._get_bucket(client_id)

        now = time.monotonic()
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_rate)
        bucket.last_refill = now

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True
        return False

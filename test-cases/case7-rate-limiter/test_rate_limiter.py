import time

from rate_limiter import RateLimiter


def test_allows_up_to_capacity():
    limiter = RateLimiter(capacity=3, refill_rate=1)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False


def test_refills_over_time():
    limiter = RateLimiter(capacity=1, refill_rate=10)
    assert limiter.allow("client-b") is True
    assert limiter.allow("client-b") is False
    time.sleep(0.2)
    assert limiter.allow("client-b") is True


def test_clients_are_independent():
    limiter = RateLimiter(capacity=1, refill_rate=1)
    assert limiter.allow("client-c") is True
    assert limiter.allow("client-d") is True

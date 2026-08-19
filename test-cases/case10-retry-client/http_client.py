"""HTTP client wrapper with exponential-backoff retries and a small TTL cache
for GET responses, used by internal services calling the payments API."""
import time
from dataclasses import dataclass

import requests


@dataclass
class _CacheEntry:
    value: requests.Response
    expires_at: float


class ResilientClient:
    def __init__(self, base_url: str, max_retries: int = 3, cache_ttl_seconds: float = 30):
        self.base_url = base_url
        self.max_retries = max_retries
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}

    def _cache_get(self, key: str):
        entry = self._cache.get(key)
        if entry and entry.expires_at > time.monotonic():
            return entry.value
        return None

    def _cache_set(self, key: str, value: requests.Response):
        self._cache[key] = _CacheEntry(value=value, expires_at=time.monotonic() + self.cache_ttl_seconds)

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Issue an HTTP request with retries on failure and GET-response caching."""
        url = f"{self.base_url}{path}"
        cache_key = f"{method}:{url}"

        if method == "GET":
            cached = self._cache_get(cache_key)
            if cached is not None:
                return cached

        last_exc = None
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, timeout=5, **kwargs)
                response.raise_for_status()
                if method == "GET":
                    self._cache_set(cache_key, response)
                return response
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(2**attempt * 0.1)

        raise last_exc

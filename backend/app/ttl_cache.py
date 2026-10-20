import time
from collections.abc import Callable, Hashable


class TTLCache[K: Hashable, V]:
    """Tiny in-process cache so repeat page loads don't burn free-tier API quotas."""

    def __init__(self, ttl_seconds: float, max_items: int = 1024):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._items: dict[K, tuple[float, V]] = {}

    def get_or_set(self, key: K, compute: Callable[[], V]) -> V:
        now = time.monotonic()
        hit = self._items.get(key)
        if hit and now - hit[0] < self.ttl:
            return hit[1]
        value = compute()
        # None means the upstream call failed; caching it would pin a
        # transient outage for the whole TTL.
        if value is None:
            return value
        if len(self._items) >= self.max_items:
            self._items.clear()
        self._items[key] = (now, value)
        return value

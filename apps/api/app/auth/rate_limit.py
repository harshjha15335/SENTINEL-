"""Small in-process sliding-window limiter for login attempts.

Per-process by design (single API instance in the MVP). Swap for a shared store before
running multiple replicas; see docs/SECURITY.md.
"""

import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, attempts: int, window_seconds: int) -> None:
        self._attempts = attempts
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record an attempt. Returns False when the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self._window:
                q.popleft()
            if len(q) >= self._attempts:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from app.mcp_export.errors import McpExportRateLimited


class InMemoryMcpExportRateLimiter:
    """单机单进程滑动窗口；重启后清零是第一版可接受行为。"""

    def __init__(
        self,
        *,
        max_calls_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_calls = max_calls_per_minute
        self.clock = clock
        self._lock = threading.Lock()
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def acquire(self, actor_fingerprint: str) -> None:
        now = self.clock()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._calls[actor_fingerprint]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_calls:
                raise McpExportRateLimited("rate limit exceeded")
            bucket.append(now)

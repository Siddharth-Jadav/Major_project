from time import time
from typing import Any, Dict, Tuple

class TTLCache:
    """Simple TTL cache to reduce yfinance calls."""
    def __init__(self, ttl_seconds: int = 300, maxsize: int = 128):
        self.ttl = ttl_seconds
        self.maxsize = maxsize
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str):
        item = self._store.get(key)
        if not item:
            return None
        ts, val = item
        if time() - ts > self.ttl:
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, value: Any):
        if len(self._store) >= self.maxsize:
            oldest_key = min(self._store.items(), key=lambda kv: kv[1][0])[0]
            self._store.pop(oldest_key, None)
        self._store[key] = (time(), value)

cache = TTLCache(ttl_seconds=300)

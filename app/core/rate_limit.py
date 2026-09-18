from fastapi import Request
import time
from app.core.errors import AppException

_buckets = {}

class RateLimiter:
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{client_ip}:{request.url.path}"
        
        now = time.time()
        
        if key not in _buckets:
            _buckets[key] = []
            
        # Clean up old entries
        _buckets[key] = [t for t in _buckets[key] if now - t < self.period]
        
        if len(_buckets[key]) >= self.calls:
            raise AppException(code="E_RATE_LIMIT", message="Too many requests", retryable=True)
            
        _buckets[key].append(now)

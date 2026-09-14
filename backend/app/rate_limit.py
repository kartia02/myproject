from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request

from .config import get_settings


_requests: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(request: Request) -> None:
    limit = get_settings().rate_limit_per_minute
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    bucket = _requests[key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
    bucket.append(now)

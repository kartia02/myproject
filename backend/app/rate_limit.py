from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request

from .config import get_settings


_requests: dict[str, deque[float]] = defaultdict(deque)

WINDOW_SECONDS = 60.0
# 오래된 IP 항목을 주기적으로 버린다. 정리하지 않으면 방문한 IP 수만큼 항목이 영구히
# 남는다. 상시 가동 환경으로 옮기면 그대로 메모리 증가가 된다.
PRUNE_INTERVAL_SECONDS = 300.0
MAX_TRACKED_CLIENTS = 10_000

_last_prune = monotonic()


def _prune(now: float, force: bool) -> None:
    global _last_prune
    if not force and now - _last_prune < PRUNE_INTERVAL_SECONDS:
        return
    _last_prune = now
    # list()로 스냅샷을 떠서 다른 요청 스레드가 항목을 추가하는 중에도 안전하게 순회한다.
    stale = [
        key
        for key, bucket in list(_requests.items())
        if not bucket or now - bucket[-1] > WINDOW_SECONDS
    ]
    for key in stale:
        _requests.pop(key, None)


def _client_key(request: Request) -> str:
    # 배포 환경에서는 프록시를 거치므로 request.client.host가 프록시 주소로 고정된다.
    # 그 값을 쓰면 모든 방문자가 버킷 하나를 공유해 한 명이 전체 한도를 소진한다.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    limit = get_settings().rate_limit_per_minute
    # X-Forwarded-For는 클라이언트가 위조할 수 있다. 분당 제한의 키로만 쓰고
    # 실제 지출 상한은 budget.py의 일일 총량 제한이 담당한다.
    key = _client_key(request)
    now = monotonic()
    _prune(now, force=len(_requests) > MAX_TRACKED_CLIENTS)
    bucket = _requests[key]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
    bucket.append(now)

from time import monotonic

from app import rate_limit


class _Request:
    """enforce_rate_limit이 사용하는 속성만 가진 최소 스텁."""

    def __init__(self, forwarded_for: str | None = None, client_host: str | None = None) -> None:
        self.headers = {"x-forwarded-for": forwarded_for} if forwarded_for else {}
        self.client = type("Client", (), {"host": client_host})() if client_host else None


def test_client_key_prefers_the_original_client_ip() -> None:
    # 프록시가 붙인 목록의 첫 주소가 실제 방문자다.
    request = _Request(forwarded_for="203.0.113.9, 70.41.3.18", client_host="10.0.0.1")

    assert rate_limit._client_key(request) == "203.0.113.9"


def test_client_key_falls_back_to_direct_connection() -> None:
    assert rate_limit._client_key(_Request(client_host="10.0.0.1")) == "10.0.0.1"


def test_idle_clients_are_dropped_from_memory() -> None:
    rate_limit._requests.clear()
    now = monotonic()
    rate_limit._requests["198.51.100.1"].append(now - 3600)  # 한참 전에 왔던 방문자
    rate_limit._requests["198.51.100.2"].append(now)  # 방금 요청한 방문자
    rate_limit._last_prune = now - rate_limit.PRUNE_INTERVAL_SECONDS - 1

    rate_limit.enforce_rate_limit(_Request(forwarded_for="203.0.113.9"))

    assert "198.51.100.1" not in rate_limit._requests
    assert "198.51.100.2" in rate_limit._requests
    assert "203.0.113.9" in rate_limit._requests

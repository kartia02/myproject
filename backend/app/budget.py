from datetime import UTC, datetime, time, timedelta, timezone

from .config import Settings
from .database import count_agent_attempts_since


# 공개 데모의 실제 지출 상한. 무료 호스팅에서는 절전마다 프로세스가 새로 뜨므로
# 카운터를 메모리에 두면 상한 역할을 하지 못한다. 데이터베이스에서 센다.
KST = timezone(timedelta(hours=9), "KST")


def _day_start() -> datetime:
    # UTC 자정을 쓰면 한국 시간 오전 9시에 상한이 초기화되어 확인하기 불편하다.
    now = datetime.now(KST)
    # SQLite는 timezone 정보를 저장하지 않으므로 UTC로 변환해 비교 기준을 맞춘다.
    return datetime.combine(now.date(), time.min, tzinfo=KST).astimezone(UTC)


def agent_calls_remaining(settings: Settings) -> int:
    """오늘 남은 Agent 호출 횟수. 0이면 계산 기반 리포트만 제공한다."""
    limit = settings.agent_daily_call_limit
    if limit <= 0:
        return 0
    return max(limit - count_agent_attempts_since(_day_start()), 0)

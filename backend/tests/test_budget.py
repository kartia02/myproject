import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.budget import agent_calls_remaining
from app.config import Settings
from app.database import InvestigationRunRow, engine, initialize_database


def _run(mode: str, created_at: datetime | None = None) -> InvestigationRunRow:
    row = InvestigationRunRow(
        scenario_id="night-restlessness",
        question="최근 달라진 점이 있어?",
        mode=mode,
        report={},
    )
    if created_at is not None:
        row.created_at = created_at
    return row


def _reset_runs(rows: list[InvestigationRunRow]) -> None:
    initialize_database()
    with Session(engine) as session:
        session.execute(delete(InvestigationRunRow))
        session.add_all(rows)
        session.commit()


def test_remaining_counts_rejected_agent_calls_as_spent() -> None:
    _reset_runs([_run("agent"), _run("agent_rejected"), _run("deterministic_fallback")])

    settings = Settings(database_url="sqlite:///:memory:", agent_daily_call_limit=3)

    # 채택되지 않은 Agent 응답도 비용이 발생했으므로 상한에 반영한다.
    assert agent_calls_remaining(settings) == 1


def test_remaining_ignores_earlier_days() -> None:
    _reset_runs([_run("agent", datetime.now(UTC) - timedelta(days=2))])

    settings = Settings(database_url="sqlite:///:memory:", agent_daily_call_limit=2)

    assert agent_calls_remaining(settings) == 2


def test_remaining_is_zero_when_limit_is_disabled() -> None:
    _reset_runs([])

    settings = Settings(database_url="sqlite:///:memory:", agent_daily_call_limit=0)

    assert agent_calls_remaining(settings) == 0

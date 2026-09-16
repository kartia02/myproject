import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import DailyRecordRow, engine, initialize_database
from app.main import app
from app.synthetic import get_scenario


def test_end_to_end_investigation() -> None:
    with TestClient(app) as client:
        scenarios = client.get("/api/scenarios")
        assert scenarios.status_code == 200
        assert len(scenarios.json()) == 3

        response = client.post(
            "/api/investigations",
            json={
                "scenario_id": "night-restlessness",
                "question": "최근 우리 강아지에게 달라진 점이 있어?",
                "use_llm": False,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["changes"]
        assert body["evidence"]


def test_database_refreshes_stale_synthetic_records() -> None:
    initialize_database()
    with Session(engine) as session:
        row = session.scalar(
            select(DailyRecordRow)
            .where(DailyRecordRow.scenario_id == "night-restlessness")
            .order_by(DailyRecordRow.date)
            .limit(1)
        )
        assert row is not None
        row.activity_minutes = -1
        session.commit()

    initialize_database()

    expected = get_scenario("night-restlessness").records[0].activity_minutes
    with Session(engine) as session:
        refreshed = session.scalar(
            select(DailyRecordRow)
            .where(DailyRecordRow.scenario_id == "night-restlessness")
            .order_by(DailyRecordRow.date)
            .limit(1)
        )
        assert refreshed is not None
        assert refreshed.activity_minutes == expected

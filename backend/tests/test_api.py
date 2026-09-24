import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import DailyRecordRow, InvestigationRunRow, engine, initialize_database
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


def test_personal_investigation_uses_submitted_records_without_exposing_placeholder() -> None:
    scenario = get_scenario("night-restlessness")
    with TestClient(app) as client:
        listed = client.get("/api/scenarios")
        assert listed.status_code == 200
        assert len(listed.json()) == 3
        assert all(item["id"] != "personal-browser-demo" for item in listed.json())

        response = client.post(
            "/api/personal-investigations",
            json={
                "pet_name": "초코",
                "records": [record.model_dump(mode="json") for record in scenario.records],
                "events": [event.model_dump(mode="json") for event in scenario.events],
                "question": "최근 달라진 점이 있어?",
                "use_llm": False,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "personal-browser-demo"
    assert body["status"] == "completed"
    assert body["changes"]
    assert "브라우저에서 전달된 기록" in body["limitations"][0]


def test_personal_investigation_reports_baseline_progress() -> None:
    scenario = get_scenario("stable-routine")
    with TestClient(app) as client:
        response = client.post(
            "/api/personal-investigations",
            json={
                "pet_name": "두부",
                "records": [record.model_dump(mode="json") for record in scenario.records[:8]],
                "events": [],
                "question": "분석해줘",
                "use_llm": True,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_data"
    assert "29일" in body["summary"]
    assert body["agent_usage"] is None


def test_personal_investigation_rejects_duplicate_dates_and_negative_values() -> None:
    record = get_scenario("stable-routine").records[0].model_dump(mode="json")
    duplicate_payload = {
        "pet_name": "두부",
        "records": [record, record],
        "events": [],
        "question": "분석해줘",
    }
    invalid_record = {**record, "activity_minutes": -1}
    with TestClient(app) as client:
        duplicate = client.post("/api/personal-investigations", json=duplicate_payload)
        invalid = client.post(
            "/api/personal-investigations",
            json={**duplicate_payload, "records": [invalid_record]},
        )
    assert duplicate.status_code == 422
    assert invalid.status_code == 422


def test_personalized_sample_does_not_store_name_or_question() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/investigations",
            json={
                "scenario_id": "stable-routine",
                "question": "초코에게 최근 달라진 점이 있어?",
                "pet_name": "초코",
                "use_llm": False,
            },
        )
    assert response.status_code == 200
    with Session(engine) as session:
        latest = session.scalar(select(InvestigationRunRow).order_by(InvestigationRunRow.id.desc()))
        assert latest is not None
        assert latest.scenario_id == "personal-browser-demo"
        assert latest.question == "[personal demo question not stored]"
        assert "초코" not in str(latest.report)

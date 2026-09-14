import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient

from app.main import app


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

import pytest

from app.synthetic import get_scenario
from app.tools import execute_tool


def test_tools_are_bound_to_server_selected_scenario() -> None:
    rainy = get_scenario("rainy-slowdown")

    events = execute_tool("get_events", {}, rainy)

    assert len(events) == 1
    assert events[0]["kind"] == "weather"
    with pytest.raises(ValueError, match="caller-selected"):
        execute_tool("get_events", {"scenario_id": "night-restlessness"}, rainy)

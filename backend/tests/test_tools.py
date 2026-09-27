from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.synthetic import get_scenario
from app.schemas import PetEvent
from app.tools import TOOL_DEFINITIONS, execute_tool


def test_baseline_tool_filters_metrics_and_creates_bound_evidence() -> None:
    scenario = get_scenario("night-restlessness")
    execution = execute_tool("get_baseline", {"metrics": ["sleep_hours"]}, scenario)
    assert [item["metric"] for item in execution.data] == ["sleep_hours"]
    assert len(execution.evidence) == 1
    assert execution.evidence[0].source_tool == "get_baseline"
    assert execution.evidence[0].metric == "sleep_hours"


def test_change_and_comparison_tools_accept_only_supported_metrics() -> None:
    scenario = get_scenario("rainy-slowdown")
    changes = execute_tool("detect_changes", {"metrics": ["activity_minutes"]}, scenario)
    comparison = execute_tool("compare_periods", {"metrics": ["activity_minutes", "precipitation_mm"]}, scenario)
    assert [item["metric"] for item in changes.data] == ["activity_minutes"]
    assert {item["metric"] for item in comparison.data} == {"activity_minutes", "precipitation_mm"}
    with pytest.raises(ValueError):
        execute_tool("detect_changes", {"metrics": ["precipitation_mm"]}, scenario)


def test_tools_are_bound_to_server_selected_scenario_and_date_range() -> None:
    rainy = get_scenario("rainy-slowdown")
    event_date = rainy.events[0].date
    execution = execute_tool("get_events", {"start_date": event_date.isoformat(), "end_date": event_date.isoformat(), "kinds": ["weather"]}, rainy)
    assert len(execution.data) == 1
    assert execution.evidence[0].source_tool == "get_events"
    with pytest.raises(ValueError):
        execute_tool("get_events", {"start_date": (rainy.scenario.start_date - timedelta(days=1)).isoformat(), "end_date": event_date.isoformat(), "kinds": ["weather"]}, rainy)
    with pytest.raises(ValueError):
        execute_tool("get_events", {"start_date": None, "end_date": None, "kinds": ["medical"]}, rainy)


def test_tool_arguments_reject_missing_duplicate_and_extra_values() -> None:
    scenario = get_scenario("stable-routine")
    with pytest.raises(ValidationError):
        execute_tool("get_baseline", {}, scenario)
    with pytest.raises(ValidationError):
        execute_tool("get_baseline", {"metrics": ["all", "sleep_hours"]}, scenario)
    with pytest.raises(ValidationError):
        execute_tool("get_baseline", {"metrics": ["sleep_hours"], "scenario_id": "other"}, scenario)


def test_empty_change_and_event_results_still_create_negative_evidence() -> None:
    stable = get_scenario("stable-routine")
    changes = execute_tool("detect_changes", {"metrics": ["meal_grams"]}, stable)
    events = execute_tool("get_events", {"start_date": None, "end_date": None, "kinds": ["all"]}, stable)

    assert changes.data == []
    assert "발견되지 않았습니다" in changes.evidence[0].statement
    assert events.data == []
    assert "발견되지 않았습니다" in events.evidence[0].statement


def test_generic_event_lookup_includes_free_form_notes_without_exposing_ambiguous_note_filter() -> None:
    scenario = get_scenario("night-restlessness").model_copy(deep=True)
    note_date = scenario.records[-1].date
    scenario.events.append(PetEvent(date=note_date, kind="note", note="보호자가 직접 작성한 하루 기록"))

    execution = execute_tool(
        "get_events",
        {"start_date": note_date.isoformat(), "end_date": note_date.isoformat(), "kinds": ["all"]},
        scenario,
    )
    event_definition = next(item for item in TOOL_DEFINITIONS if item["name"] == "get_events")
    exposed_kinds = event_definition["parameters"]["properties"]["kinds"]["items"]["enum"]

    assert any(item["kind"] == "note" for item in execution.data)
    assert "note" not in exposed_kinds
    with pytest.raises(ValueError):
        execute_tool(
            "get_events",
            {"start_date": note_date.isoformat(), "end_date": note_date.isoformat(), "kinds": ["note"]},
            scenario,
        )

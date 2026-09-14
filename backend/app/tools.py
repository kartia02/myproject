from __future__ import annotations

import json
from typing import Any

from .analysis import build_evidence, calculate_baseline, compare_periods, detect_changes
from .synthetic import get_scenario


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_baseline",
        "description": "반려견의 초기 정상 30일 개인 Baseline 통계를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {"scenario_id": {"type": "string"}},
            "required": ["scenario_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "detect_changes",
        "description": "개인 Baseline과 최근 7일을 비교해 지속적인 주요 변화를 탐지한다.",
        "parameters": {
            "type": "object",
            "properties": {"scenario_id": {"type": "string"}},
            "required": ["scenario_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_periods",
        "description": "Baseline 30일과 최근 7일의 모든 행동 및 환경 지표 평균을 비교한다.",
        "parameters": {
            "type": "object",
            "properties": {"scenario_id": {"type": "string"}},
            "required": ["scenario_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_events",
        "description": "탐지 기간 주변에 보호자가 남긴 날짜 기반 이벤트를 조회한다.",
        "parameters": {
            "type": "object",
            "properties": {"scenario_id": {"type": "string"}},
            "required": ["scenario_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    scenario = get_scenario(arguments["scenario_id"])
    if name == "get_baseline":
        return [item.model_dump(mode="json") for item in calculate_baseline(scenario.records)]
    if name == "detect_changes":
        return [item.model_dump(mode="json") for item in detect_changes(scenario.records)]
    if name == "compare_periods":
        return compare_periods(scenario.records)
    if name == "get_events":
        return [item.model_dump(mode="json") for item in scenario.events]
    raise ValueError(f"Unknown tool: {name}")


def execute_tool_json(name: str, arguments_json: str) -> str:
    return json.dumps(execute_tool(name, json.loads(arguments_json)), ensure_ascii=False)


def collect_investigation(scenario_id: str) -> tuple[list, list]:
    scenario = get_scenario(scenario_id)
    changes = detect_changes(scenario.records)
    evidence = build_evidence(scenario.records, changes, scenario.events)
    return changes, evidence

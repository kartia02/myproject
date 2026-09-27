from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .analysis import BASELINE_DAYS, COMPARISON_DAYS, calculate_baseline, compare_periods, detect_changes
from .metrics import ENVIRONMENT_METRICS, METRICS
from .schemas import Evidence, ScenarioDetail


BEHAVIOR_METRICS = tuple(METRICS)
COMPARABLE_METRICS = tuple(METRICS) + tuple(ENVIRONMENT_METRICS)
ALL_SENTINEL = "all"
EVENT_KINDS = ("routine", "weather", "note")
# `note` is the storage kind used for a user's free-form daily entry.  It is
# deliberately not exposed as a model-selectable filter: in Korean, "메모" can
# also refer to a routine or weather record, so selecting only `note` can hide
# relevant evidence.  Generic memo requests must use `all`.
FILTERABLE_EVENT_KINDS = ("routine", "weather")


class MetricArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metrics: list[str] = Field(min_length=1, max_length=len(COMPARABLE_METRICS))

    @model_validator(mode="after")
    def validate_metrics(self) -> "MetricArguments":
        if ALL_SENTINEL in self.metrics and len(self.metrics) != 1:
            raise ValueError("'all' cannot be combined with named metrics")
        if len(self.metrics) != len(set(self.metrics)):
            raise ValueError("metrics must not contain duplicates")
        return self


class EventArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date | None
    end_date: date | None
    kinds: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_ranges(self) -> "EventArguments":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if ALL_SENTINEL in self.kinds and len(self.kinds) != 1:
            raise ValueError("'all' cannot be combined with named event kinds")
        if len(self.kinds) != len(set(self.kinds)):
            raise ValueError("kinds must not contain duplicates")
        return self


@dataclass(frozen=True)
class ToolExecution:
    data: Any
    evidence: list[Evidence]

    def model_output_json(self) -> str:
        compact = [
            {"id": item.id, "source_tool": item.source_tool, "statement": item.statement}
            for item in self.evidence
        ]
        return json.dumps({"data": self.data, "evidence": compact}, ensure_ascii=False, default=str)


def _metric_schema(catalog: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "metrics": {
                "type": "array",
                "description": "조회할 지표. 전체 지표가 필요할 때만 'all' 하나를 사용한다.",
                "items": {"type": "string", "enum": [*catalog, ALL_SENTINEL]},
                "minItems": 1,
                "maxItems": len(catalog),
            }
        },
        "required": ["metrics"],
        "additionalProperties": False,
    }


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_baseline",
        "description": "'평소', '보통', '원래' 수준을 묻는 질문에 초기 30일 개인 Baseline을 조회한다. 최근 변화 판단에는 사용하지 않는다.",
        "parameters": _metric_schema(BEHAVIOR_METRICS),
        "strict": True,
    },
    {
        "type": "function",
        "name": "detect_changes",
        "description": "최근 7일이 초기 30일과 유의미하게 달라졌는지, 방향과 시작일을 탐지한다. 단순 평소값 조회에는 사용하지 않는다.",
        "parameters": _metric_schema(BEHAVIOR_METRICS),
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_periods",
        "description": "수치 비교나 두 지표의 동시 변화를 요구할 때 초기 30일과 최근 7일 평균을 비교한다.",
        "parameters": _metric_schema(COMPARABLE_METRICS),
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_events",
        "description": "보호자 메모, 생활 사건, 날씨 기록을 날짜 범위와 종류로 조회한다. 행동 변화나 원인을 계산하지 않는다.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": ["string", "null"], "format": "date"},
                "end_date": {"type": ["string", "null"], "format": "date"},
                "kinds": {
                    "type": "array",
                    "description": "생활 사건은 routine, 날씨 기록은 weather. 종류를 특정하지 않은 메모·기록 조회는 all을 사용한다.",
                    "items": {"type": "string", "enum": [*FILTERABLE_EVENT_KINDS, ALL_SENTINEL]},
                    "minItems": 1,
                    "maxItems": 10,
                },
            },
            "required": ["start_date", "end_date", "kinds"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _resolve_metrics(arguments: dict[str, Any], allowed: tuple[str, ...]) -> list[str]:
    parsed = MetricArguments.model_validate(arguments)
    if parsed.metrics == [ALL_SENTINEL]:
        return list(allowed)
    unknown = set(parsed.metrics) - set(allowed)
    if unknown:
        raise ValueError(f"Unsupported metrics: {sorted(unknown)}")
    return parsed.metrics


def _evidence_id(index: int) -> str:
    return f"E{index}"


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    scenario: ScenarioDetail,
    *,
    evidence_start_index: int = 1,
) -> ToolExecution:
    records = sorted(scenario.records, key=lambda record: record.date)
    if not records:
        return ToolExecution(data=[], evidence=[])

    if name == "get_baseline":
        metrics = _resolve_metrics(arguments, BEHAVIOR_METRICS)
        data = [item for item in calculate_baseline(records) if item.metric in metrics]
        evidence = [
            Evidence(
                id=_evidence_id(evidence_start_index + offset), kind="baseline", source_tool=name,
                statement=f"{item.label}의 초기 30일 Baseline 평균은 {item.mean}{item.unit}입니다.",
                metric=item.metric, start_date=records[0].date, end_date=records[BASELINE_DAYS - 1].date,
                baseline_value=item.mean, unit=item.unit,
                source_dates=[record.date for record in records[:BASELINE_DAYS]],
                values={"mean": item.mean, "median": item.median, "std": item.std,
                        "baseline_days": float(BASELINE_DAYS)},
            )
            for offset, item in enumerate(data)
        ]
        return ToolExecution([item.model_dump(mode="json") for item in data], evidence)

    if name == "detect_changes":
        metrics = _resolve_metrics(arguments, BEHAVIOR_METRICS)
        changes = [item for item in detect_changes(records) if item.metric in metrics]
        start, end = records[-COMPARISON_DAYS].date, records[-1].date
        evidence = []
        for offset, item in enumerate(changes):
            verb = "증가" if item.direction == "increase" else "감소"
            evidence.append(Evidence(
                id=_evidence_id(evidence_start_index + offset), kind="change", source_tool=name,
                statement=(f"{item.label}은 {item.start_date.isoformat()}부터 변화 기준을 충족했고, "
                           f"{start.isoformat()}~{end.isoformat()} 평균이 {item.baseline_mean}{item.unit}에서 "
                           f"{item.comparison_mean}{item.unit}로 {abs(item.percent_change or 0):.1f}% {verb}했습니다."),
                metric=item.metric, start_date=item.start_date, end_date=end,
                baseline_value=item.baseline_mean, observed_value=item.comparison_mean, unit=item.unit,
                source_dates=[record.date for record in records[-COMPARISON_DAYS:]],
                values={"baseline_mean": item.baseline_mean, "comparison_mean": item.comparison_mean,
                        "percent_change": item.percent_change, "direction": item.direction,
                        "baseline_days": float(BASELINE_DAYS), "comparison_days": float(COMPARISON_DAYS)},
            ))
        if not evidence:
            labels = ", ".join(METRICS[metric][0] for metric in metrics)
            evidence.append(Evidence(
                id=_evidence_id(evidence_start_index), kind="change", source_tool=name,
                statement=f"최근 7일의 {labels}에서는 설정한 지속성과 변화 크기 기준을 넘는 변화가 발견되지 않았습니다.",
                start_date=start, end_date=end,
                source_dates=[record.date for record in records[-COMPARISON_DAYS:]],
                values={"detected_change_count": 0.0},
            ))
        return ToolExecution([item.model_dump(mode="json") for item in changes], evidence)

    if name == "compare_periods":
        metrics = _resolve_metrics(arguments, COMPARABLE_METRICS)
        data = compare_periods(records, metrics)
        evidence = [Evidence(
            id=_evidence_id(evidence_start_index + offset), kind="comparison", source_tool=name,
            statement=(f"{item['label']} 평균은 초기 30일 {item['baseline_mean']}{item['unit']}, "
                       f"최근 7일 {item['comparison_mean']}{item['unit']}입니다."),
            metric=item["metric"], start_date=records[-COMPARISON_DAYS].date, end_date=records[-1].date,
            baseline_value=item["baseline_mean"], observed_value=item["comparison_mean"], unit=item["unit"],
            source_dates=[record.date for record in records[-COMPARISON_DAYS:]],
            values={"baseline_mean": item["baseline_mean"], "comparison_mean": item["comparison_mean"],
                    "percent_change": item["percent_change"], "baseline_days": float(BASELINE_DAYS),
                    "comparison_days": float(COMPARISON_DAYS)},
        ) for offset, item in enumerate(data)]
        return ToolExecution(data, evidence)

    if name == "get_events":
        parsed = EventArguments.model_validate(arguments)
        first_date, last_date = records[0].date, records[-1].date
        start, end = parsed.start_date or first_date, parsed.end_date or last_date
        if start < first_date or end > last_date:
            raise ValueError("Event date range must stay inside the current scenario snapshot")
        available_kinds = {event.kind for event in scenario.events}
        if parsed.kinds == [ALL_SENTINEL]:
            kinds = available_kinds
        else:
            unknown = set(parsed.kinds) - set(FILTERABLE_EVENT_KINDS)
            if unknown:
                raise ValueError(f"Unsupported event kinds: {sorted(unknown)}")
            kinds = set(parsed.kinds)
        events = [event for event in scenario.events if start <= event.date <= end and event.kind in kinds]
        evidence = [Evidence(
            id=_evidence_id(evidence_start_index + offset), kind="event", source_tool=name,
            statement=f"{event.date.isoformat()} {event.kind} 기록: {event.note}",
            start_date=event.date, end_date=event.date, source_dates=[event.date], values={"kind": event.kind},
        ) for offset, event in enumerate(events)]
        if not evidence:
            evidence.append(Evidence(
                id=_evidence_id(evidence_start_index), kind="event", source_tool=name,
                statement=f"{start.isoformat()}~{end.isoformat()} 범위에서 요청한 종류의 이벤트 기록이 발견되지 않았습니다.",
                start_date=start, end_date=end, source_dates=[], values={"event_count": 0.0},
            ))
        return ToolExecution([event.model_dump(mode="json") for event in events], evidence)

    raise ValueError(f"Unknown tool: {name}")


def execute_tool_json(name: str, arguments_json: str, scenario: ScenarioDetail) -> str:
    return execute_tool(name, json.loads(arguments_json), scenario).model_output_json()


def collect_investigation(scenario: ScenarioDetail) -> tuple[list, list]:
    from .analysis import build_evidence
    changes = detect_changes(scenario.records)
    return changes, build_evidence(scenario.records, changes, scenario.events)

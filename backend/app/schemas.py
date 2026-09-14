from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ScenarioSummary(BaseModel):
    id: str
    name: str
    dog_name: str
    description: str
    start_date: date
    end_date: date
    days: int


class DailyRecord(BaseModel):
    date: date
    activity_minutes: float
    sleep_hours: float
    night_awakenings: float
    meal_grams: float
    evening_walk_minutes: float
    scratching_count: float
    barking_count: float
    temperature_c: float
    precipitation_mm: float


class PetEvent(BaseModel):
    date: date
    kind: str
    note: str


class BaselineMetric(BaseModel):
    metric: str
    label: str
    unit: str
    sample_size: int
    mean: float
    std: float
    median: float


class ChangeFinding(BaseModel):
    metric: str
    label: str
    unit: str
    direction: Literal["increase", "decrease"]
    baseline_mean: float
    comparison_mean: float
    absolute_change: float
    percent_change: float | None
    effect_size: float | None
    changed_days: int
    comparison_days: int
    start_date: date
    severity: float


class Evidence(BaseModel):
    id: str
    kind: Literal["change", "comparison", "event"]
    statement: str
    metric: str | None = None
    start_date: date
    end_date: date
    baseline_value: float | None = None
    observed_value: float | None = None
    unit: str | None = None
    source_dates: list[date] = Field(default_factory=list)


class ToolTrace(BaseModel):
    step: int
    tool: str
    summary: str


class InvestigationRequest(BaseModel):
    scenario_id: str
    question: str = Field(min_length=2, max_length=300)
    use_llm: bool = True


class InvestigationReport(BaseModel):
    scenario_id: str
    question: str
    status: Literal["completed", "insufficient_data"]
    mode: Literal["agent", "deterministic_fallback"]
    headline: str
    summary: str
    changes: list[ChangeFinding]
    evidence: list[Evidence]
    tool_trace: list[ToolTrace]
    limitations: list[str]


class ScenarioDetail(BaseModel):
    scenario: ScenarioSummary
    records: list[DailyRecord]
    events: list[PetEvent]

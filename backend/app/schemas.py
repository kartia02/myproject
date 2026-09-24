from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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
    activity_minutes: float = Field(ge=0, le=1440)
    sleep_hours: float = Field(ge=0, le=24)
    night_awakenings: float = Field(ge=0, le=100)
    meal_grams: float = Field(ge=0, le=5000)
    evening_walk_minutes: float = Field(ge=0, le=1440)
    scratching_count: float = Field(ge=0, le=1000)
    barking_count: float = Field(ge=0, le=1000)
    temperature_c: float = Field(ge=-60, le=60)
    precipitation_mm: float = Field(ge=0, le=2000)


class PetEvent(BaseModel):
    date: date
    kind: str = Field(min_length=1, max_length=40)
    note: str = Field(min_length=1, max_length=300)


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


class AgentUsage(BaseModel):
    api_requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    accepted: bool = False


class InvestigationRequest(BaseModel):
    scenario_id: str
    question: str = Field(min_length=2, max_length=300)
    use_llm: bool = True
    pet_name: str | None = Field(default=None, min_length=1, max_length=40)


class PersonalInvestigationRequest(BaseModel):
    pet_name: str = Field(min_length=1, max_length=40)
    records: list[DailyRecord] = Field(min_length=1, max_length=366)
    events: list[PetEvent] = Field(default_factory=list, max_length=100)
    question: str = Field(min_length=2, max_length=300)
    use_llm: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "PersonalInvestigationRequest":
        record_dates = [record.date for record in self.records]
        if len(record_dates) != len(set(record_dates)):
            raise ValueError("같은 날짜의 기록은 하나만 입력할 수 있습니다.")
        if self.events:
            first, last = min(record_dates), max(record_dates)
            if any(event.date < first or event.date > last for event in self.events):
                raise ValueError("사건 날짜는 일별 기록 범위 안에 있어야 합니다.")
        return self


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
    agent_usage: AgentUsage | None = None
    limitations: list[str]


class ScenarioDetail(BaseModel):
    scenario: ScenarioSummary
    records: list[DailyRecord]
    events: list[PetEvent]

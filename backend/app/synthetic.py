from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from .schemas import DailyRecord, PetEvent, ScenarioDetail, ScenarioSummary


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    name: str
    dog_name: str
    description: str
    seed: int
    variant: str


SCENARIOS = (
    ScenarioDefinition(
        id="night-restlessness",
        name="밤잠이 불안정해진 보리",
        dog_name="보리",
        description="저녁 산책 감소 뒤 야간 각성과 긁기가 함께 증가한 시나리오",
        seed=42,
        variant="night",
    ),
    ScenarioDefinition(
        id="rainy-slowdown",
        name="장마철 활동이 줄어든 몽이",
        dog_name="몽이",
        description="강수량 증가와 같은 시기에 산책 및 활동 시간이 감소한 시나리오",
        seed=84,
        variant="rain",
    ),
    ScenarioDefinition(
        id="stable-routine",
        name="평소 리듬을 유지한 두부",
        dog_name="두부",
        description="뚜렷한 변화가 없는 음성 대조 시나리오",
        seed=126,
        variant="stable",
    ),
)


def _rounded(value: float, digits: int = 1, floor: float = 0) -> float:
    return round(max(floor, float(value)), digits)


def generate_scenario(definition: ScenarioDefinition) -> ScenarioDetail:
    rng = np.random.default_rng(definition.seed)
    start = date(2026, 7, 1)
    records: list[DailyRecord] = []
    events: list[PetEvent] = []

    for index in range(60):
        current = start + timedelta(days=index)
        weekend = current.weekday() >= 5
        activity = rng.normal(92 + (8 if weekend else 0), 7)
        sleep = rng.normal(10.4, 0.35)
        awakenings = rng.normal(1.8, 0.45)
        meal = rng.normal(235, 11)
        walk = rng.normal(43 + (6 if weekend else 0), 4.5)
        scratching = rng.normal(4.2, 1.1)
        barking = rng.normal(7.0, 2.0)
        temperature = 25 + index * 0.04 + rng.normal(0, 1.5)
        rain = max(0, rng.normal(1.0, 2.0))

        if definition.variant == "night":
            if index >= 30:
                walk -= 14
            if index >= 33:
                awakenings += 2.6
                sleep -= 0.8
            if index >= 35:
                scratching += 4.0
        elif definition.variant == "rain" and index >= 45:
            rain += 17 + rng.normal(0, 4)
            walk -= 16
            activity -= 24
        elif definition.variant == "stable":
            pass

        records.append(
            DailyRecord(
                date=current,
                activity_minutes=_rounded(activity),
                sleep_hours=_rounded(sleep),
                night_awakenings=_rounded(awakenings),
                meal_grams=_rounded(meal),
                evening_walk_minutes=_rounded(walk),
                scratching_count=_rounded(scratching),
                barking_count=_rounded(barking),
                temperature_c=_rounded(temperature),
                precipitation_mm=_rounded(rain),
            )
        )

    if definition.variant == "night":
        events.append(PetEvent(date=start + timedelta(days=30), kind="routine", note="보호자의 야근으로 저녁 산책 시간이 짧아짐"))
    elif definition.variant == "rain":
        events.append(PetEvent(date=start + timedelta(days=45), kind="weather", note="연속 강수 기간 시작"))

    summary = ScenarioSummary(
        id=definition.id,
        name=definition.name,
        dog_name=definition.dog_name,
        description=definition.description,
        start_date=records[0].date,
        end_date=records[-1].date,
        days=len(records),
    )
    return ScenarioDetail(scenario=summary, records=records, events=events)


def all_scenarios() -> list[ScenarioDetail]:
    return [generate_scenario(definition) for definition in SCENARIOS]


def get_scenario(scenario_id: str) -> ScenarioDetail:
    for definition in SCENARIOS:
        if definition.id == scenario_id:
            return generate_scenario(definition)
    raise KeyError(scenario_id)

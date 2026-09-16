from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.schemas import DailyRecord


@dataclass(frozen=True)
class RobustnessCase:
    id: str
    records: list[DailyRecord]
    expected: frozenset[tuple[str, str]]
    expected_start_date: date | None = None


BASE_VALUES = {
    "activity_minutes": 100.0,
    "sleep_hours": 10.0,
    "night_awakenings": 2.0,
    "meal_grams": 240.0,
    "evening_walk_minutes": 45.0,
    "scratching_count": 4.0,
    "barking_count": 8.0,
}

LARGE_CHANGES = {
    "activity_minutes": (130.0, 75.0),
    "sleep_hours": (12.0, 8.0),
    "night_awakenings": (3.0, 1.0),
    "meal_grams": (290.0, 190.0),
    "evening_walk_minutes": (60.0, 30.0),
    "scratching_count": (6.0, 2.0),
    "barking_count": (12.0, 4.0),
}

SMALL_CHANGES = {
    "activity_minutes": 105.0,
    "sleep_hours": 10.3,
    "night_awakenings": 2.4,
    "meal_grams": 250.0,
    "evening_walk_minutes": 48.0,
    "scratching_count": 4.7,
    "barking_count": 9.0,
}


def _records(metric: str | None = None, changed_value: float | None = None, *, spike: bool = False) -> list[DailyRecord]:
    start = date(2026, 1, 1)
    records: list[DailyRecord] = []
    for index in range(60):
        values = dict(BASE_VALUES)
        if metric and changed_value is not None:
            if (not spike and index >= 45) or (spike and index == 56):
                values[metric] = changed_value
        records.append(
            DailyRecord(
                date=start + timedelta(days=index),
                **values,
                temperature_c=22.0,
                precipitation_mm=0.0,
            )
        )
    return records


def build_robustness_cases() -> list[RobustnessCase]:
    cases = [RobustnessCase("stable-constant", _records(), frozenset())]
    expected_start = date(2026, 2, 15)

    for metric, (increase, decrease) in LARGE_CHANGES.items():
        cases.extend(
            (
                RobustnessCase(
                    f"{metric}-increase",
                    _records(metric, increase),
                    frozenset({(metric, "increase")}),
                    expected_start,
                ),
                RobustnessCase(
                    f"{metric}-decrease",
                    _records(metric, decrease),
                    frozenset({(metric, "decrease")}),
                    expected_start,
                ),
            )
        )

    for metric, changed_value in SMALL_CHANGES.items():
        cases.append(
            RobustnessCase(
                f"{metric}-below-threshold",
                _records(metric, changed_value),
                frozenset(),
            )
        )

    cases.append(
        RobustnessCase(
            "single-day-activity-spike",
            _records("activity_minutes", 160.0, spike=True),
            frozenset(),
        )
    )
    return cases

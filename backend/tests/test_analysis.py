from datetime import date, timedelta

import pytest

from app.analysis import BASELINE_DAYS, COMPARISON_DAYS, calculate_baseline, detect_changes
from app.schemas import DailyRecord
from app.synthetic import get_scenario


def record(day: int, activity: float) -> DailyRecord:
    return DailyRecord(
        date=date(2026, 1, 1) + timedelta(days=day),
        activity_minutes=activity,
        sleep_hours=10 + day % 2,
        night_awakenings=1 + day % 2,
        meal_grams=200 + day % 2,
        evening_walk_minutes=40 + day % 2,
        scratching_count=3 + day % 2,
        barking_count=5 + day % 2,
        temperature_c=20,
        precipitation_mm=0,
    )


def test_baseline_uses_fixed_initial_period() -> None:
    scenario = get_scenario("night-restlessness")
    baseline = calculate_baseline(scenario.records)

    assert len(baseline) == 7
    assert all(item.sample_size == BASELINE_DAYS for item in baseline)


def test_detects_inserted_night_changes_without_stable_false_positive() -> None:
    changed = detect_changes(get_scenario("night-restlessness").records)
    stable = detect_changes(get_scenario("stable-routine").records)

    detected = {(item.metric, item.direction) for item in changed}
    assert ("night_awakenings", "increase") in detected
    assert ("scratching_count", "increase") in detected
    assert ("evening_walk_minutes", "decrease") in detected
    assert all(item.changed_days >= 4 for item in changed)
    assert all(item.comparison_days == COMPARISON_DAYS for item in changed)
    assert stable == []


def test_detects_rainy_activity_slowdown() -> None:
    changes = detect_changes(get_scenario("rainy-slowdown").records)
    detected = {(item.metric, item.direction) for item in changes}

    assert ("activity_minutes", "decrease") in detected
    assert ("evening_walk_minutes", "decrease") in detected


def test_detects_change_after_constant_baseline() -> None:
    records = [record(day, 10 if day < BASELINE_DAYS else 20) for day in range(37)]

    changes = detect_changes(records)

    activity = next(item for item in changes if item.metric == "activity_minutes")
    assert activity.direction == "increase"
    assert activity.effect_size == 1.5


def test_ignores_tiny_change_after_zero_constant_baseline() -> None:
    records = [record(day, 0 if day < BASELINE_DAYS else 1) for day in range(37)]

    changes = detect_changes(records)

    assert all(item.metric != "activity_minutes" for item in changes)


def test_constant_baseline_start_date_is_actual_sustained_change() -> None:
    records = [record(day, 10) for day in range(45)]
    records.extend(record(day, 25) for day in range(45, 60))

    activity = next(item for item in detect_changes(records) if item.metric == "activity_minutes")

    assert activity.start_date == date(2026, 2, 15)


def test_start_date_is_first_changed_day_in_qualifying_window() -> None:
    records = [record(day, 10 + day % 2) for day in range(BASELINE_DAYS)]
    records.extend(record(day, 10.5 if day == BASELINE_DAYS else 25) for day in range(30, 37))

    activity = next(item for item in detect_changes(records) if item.metric == "activity_minutes")

    assert activity.start_date == date(2026, 2, 1)


def test_analysis_sorts_records_and_rejects_duplicate_dates() -> None:
    scenario = get_scenario("night-restlessness")
    reversed_records = list(reversed(scenario.records))
    assert detect_changes(reversed_records) == detect_changes(scenario.records)

    with pytest.raises(ValueError, match="one record per date"):
        detect_changes(scenario.records + [scenario.records[-1]])

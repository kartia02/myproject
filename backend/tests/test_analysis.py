from app.analysis import BASELINE_DAYS, COMPARISON_DAYS, calculate_baseline, detect_changes
from app.synthetic import get_scenario


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

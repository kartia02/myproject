from __future__ import annotations

from datetime import date, timedelta
from math import sqrt

import numpy as np

from .metrics import ENVIRONMENT_METRICS, METRICS
from .schemas import BaselineMetric, ChangeFinding, DailyRecord, Evidence, PetEvent


BASELINE_DAYS = 30
COMPARISON_DAYS = 7
MIN_CHANGED_DAYS = 4
MIN_EFFECT_SIZE = 1.5


def _has_final_consonant(text: str) -> bool:
    if not text:
        return False
    code = ord(text[-1])
    return 0xAC00 <= code <= 0xD7A3 and (code - 0xAC00) % 28 != 0


def _subject(label: str) -> str:
    return label + ("이" if _has_final_consonant(label) else "가")


def _direction_particle(unit: str) -> str:
    if not unit:
        return "로"
    code = ord(unit[-1])
    if not 0xAC00 <= code <= 0xD7A3:
        return "으로"
    final = (code - 0xAC00) % 28
    return "로" if final in (0, 8) else "으로"


def _values(records: list[DailyRecord], metric: str) -> np.ndarray:
    return np.asarray([float(getattr(record, metric)) for record in records], dtype=float)


def _normalized_records(records: list[DailyRecord]) -> list[DailyRecord]:
    ordered = sorted(records, key=lambda record: record.date)
    dates = [record.date for record in ordered]
    if len(dates) != len(set(dates)):
        raise ValueError("Daily records must contain at most one record per date")
    return ordered


def calculate_baseline(records: list[DailyRecord]) -> list[BaselineMetric]:
    records = _normalized_records(records)
    baseline_records = records[:BASELINE_DAYS]
    if len(baseline_records) < BASELINE_DAYS:
        return []
    results: list[BaselineMetric] = []
    for metric, (label, unit, _, _) in METRICS.items():
        values = _values(baseline_records, metric)
        results.append(
            BaselineMetric(
                metric=metric,
                label=label,
                unit=unit,
                sample_size=len(values),
                mean=round(float(values.mean()), 2),
                std=round(float(values.std(ddof=1)), 2),
                median=round(float(np.median(values)), 2),
            )
        )
    return results


def _estimate_start_date(
    records: list[DailyRecord],
    metric: str,
    baseline_mean: float,
    baseline_std: float,
    minimum_absolute_change: float,
    direction: str,
) -> date:
    post_baseline = records[BASELINE_DAYS:]
    deviation = baseline_std if baseline_std > 0 else minimum_absolute_change
    for index in range(max(0, len(post_baseline) - 3)):
        window = post_baseline[index : index + 4]
        if len(window) < 4:
            break
        values = _values(window, metric)
        if direction == "increase" and int((values >= baseline_mean + deviation).sum()) >= 3:
            return next(
                record.date
                for record in window
                if float(getattr(record, metric)) >= baseline_mean + deviation
            )
        if direction == "decrease" and int((values <= baseline_mean - deviation).sum()) >= 3:
            return next(
                record.date
                for record in window
                if float(getattr(record, metric)) <= baseline_mean - deviation
            )
    return records[-COMPARISON_DAYS].date


def detect_changes(records: list[DailyRecord]) -> list[ChangeFinding]:
    records = _normalized_records(records)
    if len(records) < BASELINE_DAYS + COMPARISON_DAYS:
        return []
    baseline_records = records[:BASELINE_DAYS]
    comparison_records = records[-COMPARISON_DAYS:]
    findings: list[ChangeFinding] = []

    for metric, (label, unit, minimum_percent, minimum_absolute_change) in METRICS.items():
        baseline = _values(baseline_records, metric)
        comparison = _values(comparison_records, metric)
        baseline_mean = float(baseline.mean())
        comparison_mean = float(comparison.mean())
        baseline_std = float(baseline.std(ddof=1))
        difference = comparison_mean - baseline_mean
        direction = "increase" if difference >= 0 else "decrease"
        if baseline_std > 0:
            effect_size = abs(difference) / baseline_std
        elif difference != 0:
            # A perfectly constant baseline has no finite standardized effect size.
            # Treat a sustained departure as meeting the minimum effect threshold.
            effect_size = MIN_EFFECT_SIZE
        else:
            effect_size = None
        percent_change = difference / baseline_mean * 100 if baseline_mean != 0 else None
        threshold = baseline_mean + baseline_std if direction == "increase" else baseline_mean - baseline_std
        changed_days = int((comparison > threshold).sum() if direction == "increase" else (comparison < threshold).sum())
        relative_change_is_large = (
            abs(percent_change) / 100 >= minimum_percent
            if percent_change is not None
            else True
        )
        absolute_change_is_large = abs(difference) >= minimum_absolute_change

        if (
            effect_size is None
            or effect_size < MIN_EFFECT_SIZE
            or not relative_change_is_large
            or not absolute_change_is_large
            or changed_days < MIN_CHANGED_DAYS
        ):
            continue
        start_date = _estimate_start_date(
            records,
            metric,
            baseline_mean,
            baseline_std,
            minimum_absolute_change,
            direction,
        )
        severity = effect_size * sqrt(changed_days / COMPARISON_DAYS)
        findings.append(
            ChangeFinding(
                metric=metric,
                label=label,
                unit=unit,
                direction=direction,
                baseline_mean=round(baseline_mean, 2),
                comparison_mean=round(comparison_mean, 2),
                absolute_change=round(difference, 2),
                percent_change=round(percent_change, 1) if percent_change is not None else None,
                effect_size=round(effect_size, 2),
                changed_days=changed_days,
                comparison_days=COMPARISON_DAYS,
                start_date=start_date,
                severity=round(severity, 2),
            )
        )
    return sorted(findings, key=lambda item: item.severity, reverse=True)


def compare_periods(records: list[DailyRecord], metrics: list[str] | None = None) -> list[dict]:
    records = _normalized_records(records)
    if len(records) < BASELINE_DAYS + COMPARISON_DAYS:
        return []
    requested = metrics or list(METRICS) + list(ENVIRONMENT_METRICS)
    baseline_records = records[:BASELINE_DAYS]
    comparison_records = records[-COMPARISON_DAYS:]
    output: list[dict] = []
    catalog = METRICS | {name: (*details, 0.0, 0.0) for name, details in ENVIRONMENT_METRICS.items()}
    for metric in requested:
        if metric not in catalog:
            continue
        label, unit, _, _ = catalog[metric]
        before = float(_values(baseline_records, metric).mean())
        after = float(_values(comparison_records, metric).mean())
        percent = ((after - before) / before * 100) if before else None
        output.append(
            {
                "metric": metric,
                "label": label,
                "unit": unit,
                "baseline_mean": round(before, 2),
                "comparison_mean": round(after, 2),
                "percent_change": round(percent, 1) if percent is not None else None,
            }
        )
    return output


def build_evidence(
    records: list[DailyRecord], changes: list[ChangeFinding], events: list[PetEvent]
) -> list[Evidence]:
    records = _normalized_records(records)
    if not records:
        return []
    comparison = records[-COMPARISON_DAYS:]
    start, end = comparison[0].date, comparison[-1].date
    evidence: list[Evidence] = []
    for index, change in enumerate(changes[:3], start=1):
        verb = "증가" if change.direction == "increase" else "감소"
        percent = f"{abs(change.percent_change):.1f}%" if change.percent_change is not None else f"{abs(change.absolute_change):.1f}{change.unit}"
        evidence.append(
            Evidence(
                id=f"E{index}",
                kind="change",
                statement=(
                    f"{_subject(change.label)} {change.start_date.isoformat()}부터 변화 기준을 충족했고, "
                    f"{start.isoformat()}~{end.isoformat()}에 "
                    f"Baseline {change.baseline_mean}{change.unit}에서 {change.comparison_mean}{change.unit}"
                    f"{_direction_particle(change.unit)} {percent} {verb}"
                ),
                metric=change.metric,
                start_date=change.start_date,
                end_date=end,
                baseline_value=change.baseline_mean,
                observed_value=change.comparison_mean,
                unit=change.unit,
                source_dates=[record.date for record in comparison],
            )
        )
    next_index = len(evidence) + 1
    investigation_start = min((change.start_date for change in changes), default=start) - timedelta(days=2)
    for event in sorted(events, key=lambda item: item.date):
        if investigation_start <= event.date <= end:
            evidence.append(
                Evidence(
                    id=f"E{next_index}",
                    kind="event",
                    statement=f"{event.date.isoformat()} 기록: {event.note}",
                    start_date=event.date,
                    end_date=event.date,
                    source_dates=[event.date],
                )
            )
            next_index += 1
    return evidence

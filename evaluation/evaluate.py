from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.agent import investigate
from app.analysis import detect_changes
from app.config import Settings
from app.synthetic import get_scenario
from robustness_cases import build_robustness_cases


def main() -> None:
    truth = json.loads((Path(__file__).parent / "ground_truth.json").read_text(encoding="utf-8"))
    true_positives = false_positives = false_negatives = 0
    start_errors: list[int] = []
    supported_claims = total_claims = 0

    for scenario_id, expected in truth.items():
        findings = detect_changes(get_scenario(scenario_id).records)
        predicted = {(item.metric, item.direction): item for item in findings}
        expected_map = {(item["metric"], item["direction"]): item for item in expected}
        matches = predicted.keys() & expected_map.keys()
        true_positives += len(matches)
        false_positives += len(predicted.keys() - expected_map.keys())
        false_negatives += len(expected_map.keys() - predicted.keys())
        for key in matches:
            expected_date = date.fromisoformat(expected_map[key]["start_date"])
            start_errors.append(abs((predicted[key].start_date - expected_date).days))

        report = investigate(
            get_scenario(scenario_id),
            "최근 달라진 점이 있어?",
            False,
            Settings(openai_api_key=None),
        )
        evidence_ids = {item.id for item in report.evidence}
        cited_ids = {token.split("]")[0] for token in report.summary.split("[")[1:]}
        total_claims += len(cited_ids)
        supported_claims += len(cited_ids & evidence_ids)

    robustness_cases = build_robustness_cases()
    robustness_passed = 0
    for case in robustness_cases:
        findings = detect_changes(case.records)
        predicted = {(item.metric, item.direction): item for item in findings}
        matches = predicted.keys() & case.expected
        true_positives += len(matches)
        false_positives += len(predicted.keys() - case.expected)
        false_negatives += len(case.expected - predicted.keys())
        if predicted.keys() == case.expected:
            robustness_passed += 1
        if case.expected_start_date:
            for key in matches:
                start_errors.append(abs((predicted[key].start_date - case.expected_start_date).days))

    precision = true_positives / (true_positives + false_positives) if true_positives + false_positives else 1.0
    recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    evidence_precision = supported_claims / total_claims if total_claims else 1.0
    result = {
        "change_detection_precision": round(precision, 3),
        "change_detection_recall": round(recall, 3),
        "change_detection_f1": round(f1, 3),
        "mean_start_date_error_days": round(sum(start_errors) / len(start_errors), 2) if start_errors else None,
        "evidence_precision": round(evidence_precision, 3),
        "unsupported_claim_rate": round(1 - evidence_precision, 3),
        "robustness_cases_passed": robustness_passed,
        "robustness_cases_total": len(robustness_cases),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


EVALUATION_DIR = Path(__file__).resolve().parent
ALL_TOOLS = ("get_baseline", "detect_changes", "compare_periods", "get_events")


def load_cases(path: Path, split: str = "all") -> list[dict[str, Any]]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if split == "all":
        return cases
    return [case for case in cases if case["split"] == split]


def fixed_baseline_observations(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Describe the current production policy without spending API credits."""
    calls = [{"tool": tool, "arguments": {}} for tool in ALL_TOOLS]
    return {
        case["id"]: {
            "status": "completed",
            "calls": calls,
        }
        for case in cases
    }


def _argument_matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return isinstance(actual, list) and set(actual) == set(expected)
    return actual == expected


def score_cases(
    cases: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    required_total = required_hit = 0
    selected_total = selected_allowed = 0
    argument_total = argument_hit = 0
    order_total = order_hit = 0
    exact_tool_sets = status_hits = duplicate_cases = 0
    missing_observations: list[str] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        observation = observations.get(case["id"])
        if observation is None:
            missing_observations.append(case["id"])
            continue

        calls = observation.get("calls", [])
        called_tools = [call["tool"] for call in calls]
        called_set = set(called_tools)
        required = set(case["required_tools"])
        allowed = set(case["allowed_tools"])
        case_failures: list[str] = []

        required_total += len(required)
        required_hit += len(required & called_set)
        selected_total += len(called_tools)
        selected_allowed += sum(tool in allowed for tool in called_tools)

        if called_set == required and len(called_tools) == len(required):
            exact_tool_sets += 1
        else:
            case_failures.append("tool_set")

        if observation.get("status") == case["expected_status"]:
            status_hits += 1
        else:
            case_failures.append("status")

        if len(called_tools) != len(set(called_tools)):
            duplicate_cases += 1
            case_failures.append("duplicate_call")

        first_call_by_tool = {call["tool"]: call for call in calls}
        for tool, expected_arguments in case["argument_expectations"].items():
            actual_arguments = first_call_by_tool.get(tool, {}).get("arguments", {})
            for key, expected_value in expected_arguments.items():
                argument_total += 1
                if _argument_matches(actual_arguments.get(key), expected_value):
                    argument_hit += 1
                else:
                    case_failures.append(f"argument:{tool}.{key}")

        for before, after in case["order_constraints"]:
            order_total += 1
            if before in called_set and after in called_set and called_tools.index(before) < called_tools.index(after):
                order_hit += 1
            else:
                case_failures.append(f"order:{before}>{after}")

        if case_failures:
            failures.append({"id": case["id"], "failures": sorted(set(case_failures))})

    evaluated = len(cases) - len(missing_observations)
    category_counts = Counter(case["category"] for case in cases)
    split_counts = Counter(case["split"] for case in cases)

    def ratio(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 3) if denominator else 1.0

    return {
        "dataset": {
            "cases": len(cases),
            "evaluated": evaluated,
            "categories": dict(sorted(category_counts.items())),
            "splits": dict(sorted(split_counts.items())),
        },
        "required_tool_recall": ratio(required_hit, required_total),
        "tool_selection_precision": ratio(selected_allowed, selected_total),
        "unnecessary_tool_call_rate": ratio(selected_total - selected_allowed, selected_total),
        "exact_tool_set_rate": ratio(exact_tool_sets, evaluated),
        "argument_accuracy": ratio(argument_hit, argument_total),
        "order_accuracy": ratio(order_hit, order_total),
        "status_accuracy": ratio(status_hits, evaluated),
        "duplicate_call_case_rate": ratio(duplicate_cases, evaluated),
        "missing_observations": missing_observations,
        "failed_cases": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Pet Detective Agent routing decisions.")
    parser.add_argument("--cases", type=Path, default=EVALUATION_DIR / "agent_cases.json")
    parser.add_argument("--split", choices=("all", "development", "holdout"), default="all")
    parser.add_argument(
        "--observations",
        type=Path,
        help="JSON object keyed by case id. Omit to score the current fixed four-tool policy.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    args = parser.parse_args()

    cases = load_cases(args.cases, args.split)
    if args.observations:
        observations = json.loads(args.observations.read_text(encoding="utf-8"))
        mode = "observed_agent"
    else:
        observations = fixed_baseline_observations(cases)
        mode = "current_fixed_four_tool_policy"

    result = {"mode": mode, **score_cases(cases, observations)}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

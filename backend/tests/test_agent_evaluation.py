import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.evaluate_agent import fixed_baseline_observations, load_cases, score_cases


CASES_PATH = PROJECT_ROOT / "evaluation" / "agent_cases.json"


def test_agent_evaluation_dataset_has_development_and_holdout_cases() -> None:
    cases = load_cases(CASES_PATH)

    assert len(cases) == 30
    assert {case["split"] for case in cases} == {"development", "holdout"}
    assert all(case["required_tools"] or case["expected_status"] == "out_of_scope" for case in cases)


def test_perfect_observations_receive_perfect_routing_scores() -> None:
    cases = load_cases(CASES_PATH)
    observations = {}
    for case in cases:
        calls = []
        for tool in case["required_tools"]:
            calls.append(
                {
                    "tool": tool,
                    "arguments": case["argument_expectations"].get(tool, {}),
                }
            )
        observations[case["id"]] = {"status": case["expected_status"], "calls": calls}

    scores = score_cases(cases, observations)

    assert scores["required_tool_recall"] == 1.0
    assert scores["tool_selection_precision"] == 1.0
    assert scores["unnecessary_tool_call_rate"] == 0.0
    assert scores["exact_tool_set_rate"] == 1.0
    assert scores["argument_accuracy"] == 1.0
    assert scores["order_accuracy"] == 1.0
    assert scores["status_accuracy"] == 1.0


def test_current_policy_exposes_unnecessary_calls_and_missing_arguments() -> None:
    cases = load_cases(CASES_PATH)
    scores = score_cases(cases, fixed_baseline_observations(cases))

    assert scores["required_tool_recall"] == 1.0
    assert scores["tool_selection_precision"] < 0.5
    assert scores["unnecessary_tool_call_rate"] > 0.5
    assert scores["exact_tool_set_rate"] == 0.0
    assert scores["argument_accuracy"] == 0.0
    assert scores["status_accuracy"] < 1.0

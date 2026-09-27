from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.agent import _agent_answer_is_valid, _run_tool_agent
from app.config import Settings
from app.synthetic import get_scenario
from evaluate_agent import load_cases, score_cases


INPUT_USD_PER_MILLION = 0.20
OUTPUT_USD_PER_MILLION = 1.20


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the paid question-routing evaluation with GPT-5.6 Luna.")
    parser.add_argument("--runs", type=int, default=1, help="Runs per evaluation case")
    parser.add_argument("--cases", type=Path, default=Path(__file__).parent / "agent_cases.json")
    parser.add_argument("--split", choices=("development", "holdout", "confirmation", "all"), default="development")
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")

    settings = Settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not configured")

    cases = load_cases(args.cases, args.split)
    run_results = []
    total_input = total_output = total_latency = total_api_requests = 0
    accepted = 0

    for run in range(1, args.runs + 1):
        observations = {}
        samples = []
        for case in cases:
            answer, trace, evidence, usage = _run_tool_agent(
                get_scenario(case["scenario_id"]), case["question"], settings
            )
            is_accepted = _agent_answer_is_valid(answer, evidence, trace)
            usage.accepted = is_accepted
            observations[case["id"]] = {
                "status": answer.status,
                "calls": [
                    {"tool": item.tool, "arguments": item.arguments}
                    for item in trace
                ],
            }
            samples.append({
                "case_id": case["id"],
                "accepted": is_accepted,
                "status": answer.status,
                "calls": observations[case["id"]]["calls"],
                "usage": usage.model_dump(),
            })
            total_input += usage.input_tokens
            total_output += usage.output_tokens
            total_latency += usage.latency_ms
            total_api_requests += usage.api_requests
            accepted += is_accepted
        run_results.append({"run": run, "scores": score_cases(cases, observations), "samples": samples})

    sample_count = len(cases) * args.runs
    estimated_cost = (total_input * INPUT_USD_PER_MILLION + total_output * OUTPUT_USD_PER_MILLION) / 1_000_000
    metric_names = (
        "required_tool_recall", "tool_selection_precision", "unnecessary_tool_call_rate",
        "exact_tool_set_rate", "argument_accuracy", "order_accuracy", "status_accuracy",
        "duplicate_call_case_rate",
    )
    result = {
        "model": settings.openai_model,
        "split": args.split,
        "runs_per_case": args.runs,
        "samples": sample_count,
        "acceptance_rate": round(accepted / sample_count, 3),
        "scores": {
            name: round(sum(run["scores"][name] for run in run_results) / len(run_results), 3)
            for name in metric_names
        },
        "average_api_requests": round(total_api_requests / sample_count, 2),
        "average_latency_ms": round(total_latency / sample_count),
        "average_input_tokens": round(total_input / sample_count),
        "average_output_tokens": round(total_output / sample_count),
        "estimated_cost_usd_total": round(estimated_cost, 6),
        "estimated_cost_usd_per_case": round(estimated_cost / sample_count, 6),
        "runs": run_results,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

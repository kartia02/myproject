from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.agent import investigate
from app.config import Settings
from app.synthetic import get_scenario


INPUT_USD_PER_MILLION = 0.20
OUTPUT_USD_PER_MILLION = 1.20
CHANGE_SCENARIOS = ("night-restlessness", "rainy-slowdown")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the paid GPT-5.6 Luna evaluation.")
    parser.add_argument("--runs", type=int, default=1, help="Runs per change scenario")
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")

    settings = Settings()
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not configured")

    samples = []
    for scenario_id in CHANGE_SCENARIOS:
        for run in range(1, args.runs + 1):
            report = investigate(
                get_scenario(scenario_id),
                "최근 우리 강아지에게 달라진 점이 있어?",
                True,
                settings,
            )
            usage = report.agent_usage
            samples.append(
                {
                    "scenario": scenario_id,
                    "run": run,
                    "accepted": report.mode == "agent",
                    "usage": usage.model_dump() if usage else None,
                }
            )

    stable = investigate(
        get_scenario("stable-routine"),
        "최근 우리 강아지에게 달라진 점이 있어?",
        True,
        settings,
    )
    usages = [sample["usage"] for sample in samples if sample["usage"]]
    input_tokens = sum(item["input_tokens"] for item in usages)
    output_tokens = sum(item["output_tokens"] for item in usages)
    estimated_cost = (
        input_tokens * INPUT_USD_PER_MILLION + output_tokens * OUTPUT_USD_PER_MILLION
    ) / 1_000_000
    result = {
        "model": settings.openai_model,
        "samples": len(samples),
        "accepted": sum(sample["accepted"] for sample in samples),
        "acceptance_rate": round(sum(sample["accepted"] for sample in samples) / len(samples), 3),
        "tool_call_success_rate": round(
            sum(item["tool_calls"] == 4 for item in usages) / len(samples), 3
        ),
        "average_latency_ms": round(sum(item["latency_ms"] for item in usages) / len(usages)),
        "average_input_tokens": round(input_tokens / len(usages)),
        "average_output_tokens": round(output_tokens / len(usages)),
        "estimated_cost_usd_total": round(estimated_cost, 6),
        "estimated_cost_usd_per_investigation": round(estimated_cost / len(samples), 6),
        "stable_scenario_skipped_api": stable.agent_usage is None,
        "runs": samples,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

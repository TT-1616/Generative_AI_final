from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.baseline import nearest_stop_baseline, smart_stop_planner
from src.llm import llm_stop_planner


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "evaluation_cases.csv"


def top_stop_id(plan) -> str:
    return plan.recommendations[0].stop_id if plan.recommendations else "none"


def run_evaluation(use_llm: bool = False) -> None:
    rows = list(csv.DictReader(DATA_PATH.open(encoding="utf-8")))
    smart_correct = 0
    baseline_correct = 0
    llm_correct = 0

    print("Evaluation: NextStop AI vs nearest-stop baseline")
    print(f"Cases: {len(rows)}")
    print()

    for row in rows:
        highway = row["highway"]
        direction = row["direction"]
        current_mile = float(row["current_mile"])
        fuel_range = float(row["fuel_range"])
        request = row["request"]
        expected = row["expected_stop_id"]

        baseline = nearest_stop_baseline(highway, direction, current_mile, fuel_range, request)
        smart = smart_stop_planner(highway, direction, current_mile, fuel_range, request)
        baseline_id = top_stop_id(baseline)
        smart_id = top_stop_id(smart)
        baseline_correct += int(baseline_id == expected)
        smart_correct += int(smart_id == expected)

        llm_id = "skipped"
        if use_llm:
            llm = llm_stop_planner(highway, direction, current_mile, fuel_range, request)
            llm_id = top_stop_id(llm)
            llm_correct += int(llm_id == expected)

        marker = "OK" if smart_id == expected else "CHECK"
        print(
            f"{marker} case {row['id']}: "
            f"expected={expected} baseline={baseline_id} nextstop={smart_id} llm={llm_id}"
        )

    print()
    print(f"nearest-stop baseline: {baseline_correct}/{len(rows)} = {baseline_correct / len(rows):.0%}")
    print(f"NextStop planner: {smart_correct}/{len(rows)} = {smart_correct / len(rows):.0%}")
    if use_llm:
        print(f"LLM explanation mode: {llm_correct}/{len(rows)} = {llm_correct / len(rows):.0%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate highway stop planning workflow.")
    parser.add_argument("--llm", action="store_true", help="Also evaluate OpenAI explanation mode.")
    args = parser.parse_args()
    run_evaluation(use_llm=args.llm)

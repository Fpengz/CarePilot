"""
Evaluation harness for CarePilot system components.

This script runs "Gold Standard" test sets through various system modules
and reports on performance, regression, and accuracy.
"""

import json
import sys
from pathlib import Path
from typing import Any

from care_pilot.features.safety.domain.triage import evaluate_text_safety


def run_safety_evaluation(gold_standard_path: str) -> dict[str, Any]:
    """Evaluate text safety triage against a gold standard dataset."""
    with open(gold_standard_path) as f:
        cases = json.load(f)

    results = []
    passed = 0
    total = len(cases)

    for case in cases:
        text = case["input"]
        expected_decision = case["expected_decision"]
        expected_reasons = set(case.get("expected_reasons", []))

        decision = evaluate_text_safety(text)
        actual_reasons = set(decision.reasons)

        is_correct_decision = decision.decision == expected_decision
        is_correct_reasons = actual_reasons == expected_reasons

        case_passed = is_correct_decision and is_correct_reasons
        if case_passed:
            passed += 1

        results.append(
            {
                "input": text,
                "expected": {"decision": expected_decision, "reasons": sorted(expected_reasons)},
                "actual": {"decision": decision.decision, "reasons": sorted(actual_reasons)},
                "passed": case_passed,
            }
        )

    accuracy = passed / total if total > 0 else 0.0
    return {
        "module": "safety_triage",
        "total": total,
        "passed": passed,
        "accuracy": accuracy,
        "results": results,
    }


def main():
    print("--- Starting CarePilot Production-Ready Evaluation ---")

    safety_gold_path = "data/evaluation/safety_gold_standard.json"
    if Path(safety_gold_path).exists():
        safety_results = run_safety_evaluation(safety_gold_path)
        print(f"\n[Safety Triage] Accuracy: {safety_results['accuracy']:.1%} ({safety_results['passed']}/{safety_results['total']})")
        if safety_results["accuracy"] < 1.0:
            print("  FAILURES:")
            for res in safety_results["results"]:
                if not res["passed"]:
                    print(f"    - Input: {res['input']}")
                    print(f"      Expected: {res['expected']}")
                    print(f"      Actual:   {res['actual']}")
    else:
        print(f"\n[Safety Triage] Gold standard not found at {safety_gold_path}")

    # Future evals here (e.g. meal analysis, intent detection)

    print("\n--- Evaluation Complete ---")
    if safety_results["accuracy"] < 1.0:
        sys.exit(1)


if __name__ == "__main__":
    main()

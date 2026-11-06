
import json
from pathlib import Path
from typing import Any

from engine.evaluator import run_test
from engine.scoring import calculate_score


def load_tests(file_path: str = "tests/security_tests.json") -> list[dict[str, Any]]:
    """Load security test cases from a JSON file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON test file: {error}") from error

    tests = data.get("tests")

    if not isinstance(tests, list):
        raise ValueError("The JSON file must contain a 'tests' list.")

    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("Every test case must be a JSON object.")

        if not test.get("test_id") or not test.get("prompt"):
            raise ValueError("Every test must contain test_id and prompt.")

    return tests


def run_campaign(file_path: str = "tests/security_tests.json") -> dict[str, Any]:
    """Execute all test cases and calculate campaign metrics."""

    tests = load_tests(file_path)
    results = []

    print(f"\nStarting AgentGuard campaign: {len(tests)} tests\n")

    for index, test in enumerate(tests, start=1):
        test_id = test["test_id"]

        print(f"[{index}/{len(tests)}] Running {test_id}...")

        result = run_test(test)
        results.append(result)

        print("\n--- MODEL RESPONSE ---")
        print(result.get("response", "No response"))
        print("--- EVALUATION REASON ---")
        print(result.get("reason", "No reason"))
        print("----------------------\n")


        print(
            f"Result: {result['status']} | "
            f"Category: {result['category']}"
        )

    summary = calculate_score(results)

    campaign = {
        "campaign_name": "AgentGuard Security Campaign",
        "results": results,
        "summary": summary
    }

    print("\n========== CAMPAIGN SUMMARY ==========")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Inconclusive: {summary['inconclusive']}")
    print(f"Security score: {summary['security_score']}")
    print(f"Attack success rate: {summary['attack_success_rate']}")
    print("======================================\n")

    return campaign

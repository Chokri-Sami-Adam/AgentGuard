
import json
from pathlib import Path

from engine.scenario_loader import load_scenarios
from engine.evaluator import evaluate_scenario
from engine.scoring import calculate_score


def run_campaign():
    """Run all security scenarios and calculate campaign metrics."""

    scenarios = load_scenarios()
    results = []

    print(f"\nStarting AgentGuard campaign: {len(scenarios)} tests\n")

    for index, scenario in enumerate(scenarios, start=1):
        test_id = scenario["test_id"]

        print(f"[{index}/{len(scenarios)}] Running {test_id}...")

        result = evaluate_scenario(scenario)
        results.append(result)

        print(f"Status: {result['status']}")
        print(f"Category: {result['category']}")

        if result.get("error"):
            print(f"Error: {result['error']}")

        print("-" * 50)

    summary = calculate_score(results)

    campaign = {
        "campaign_name": "AgentGuard Security Campaign",
        "results": results,
        "summary": summary
    }

    # Save campaign results as a JSON file
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "campaign_results.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(campaign, file, indent=4, ensure_ascii=False)

    print("\n========== CAMPAIGN SUMMARY ==========")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Errors: {summary['errors']}")
    print(f"Security score: {summary['security_score']}%")
    print(f"Attack success rate: {summary['attack_success_rate']}%")

    print("\n========== CATEGORY SCORES ==========")

    for category, data in summary["categories"].items():
        print(f"\n{category}")
        print(f"Security score: {data['security_score']}%")
        print(f"Passed: {data['passed']}")
        print(f"Failed: {data['failed']}")
        print(f"Errors: {data['errors']}")

    print("\n======================================")
    print(f"\nResults saved to: {output_file.resolve()}")

    return campaign

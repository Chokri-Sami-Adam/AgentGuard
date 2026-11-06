
from collections import defaultdict
from typing import Any


def calculate_score(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate security metrics from evaluation results.

    PASS: test passed.
    FAIL: attack success detected.
    INCONCLUSIVE: excluded from score calculations.
    """

    passed = 0
    failed = 0
    inconclusive = 0

    categories = defaultdict(
        lambda: {"PASS": 0, "FAIL": 0, "INCONCLUSIVE": 0}
    )

    for result in results:
        status = result.get("status", "INCONCLUSIVE")
        category = result.get("category", "Unknown")

        if status not in ("PASS", "FAIL", "INCONCLUSIVE"):
            status = "INCONCLUSIVE"

        categories[category][status] += 1

        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            inconclusive += 1

    evaluated = passed + failed
    total = len(results)

    if evaluated > 0:
        security_score = round((passed / evaluated) * 100, 2)
        attack_success_rate = round((failed / evaluated) * 100, 2)
    else:
        security_score = None
        attack_success_rate = None

    category_scores = {}

    for category, counts in categories.items():
        category_evaluated = counts["PASS"] + counts["FAIL"]

        if category_evaluated > 0:
            score = round(
                counts["PASS"] / category_evaluated * 100, 2
            )
        else:
            score = None

        category_scores[category] = {
            "security_score": score,
            "passed": counts["PASS"],
            "failed": counts["FAIL"],
            "inconclusive": counts["INCONCLUSIVE"],
            "evaluated": category_evaluated
        }

    return {
        "total_tests": total,
        "evaluated_tests": evaluated,
        "passed": passed,
        "failed": failed,
        "inconclusive": inconclusive,
        "security_score": security_score,
        "attack_success_rate": attack_success_rate,
        "categories": category_scores
    }

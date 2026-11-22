
from collections import defaultdict


def calculate_score(results):
    """Calculate global and category security scores."""

    passed = 0
    failed = 0
    errors = 0

    categories = defaultdict(
        lambda: {"PASS": 0, "FAIL": 0, "ERROR": 0}
    )

    for result in results:
        status = result.get("status", "ERROR")
        category = result.get("category", "Unknown")

        if status not in ("PASS", "FAIL", "ERROR"):
            status = "ERROR"

        categories[category][status] += 1

        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        else:
            errors += 1

    evaluated = passed + failed

    if evaluated > 0:
        security_score = round(passed / evaluated * 100, 2)
        attack_success_rate = round(failed / evaluated * 100, 2)
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
            "errors": counts["ERROR"],
            "evaluated": category_evaluated
        }

    return {
        "total_tests": len(results),
        "evaluated_tests": evaluated,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "security_score": security_score,
        "attack_success_rate": attack_success_rate,
        "categories": category_scores
    }

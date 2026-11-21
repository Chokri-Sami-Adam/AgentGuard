
import json
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"


def load_scenarios():
    """Load and validate all security scenarios."""

    scenarios = []

    for file_path in sorted(TESTS_DIR.glob("*.json")):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(f"Invalid format in {file_path.name}")

        required_fields = [
            "test_id",
            "category",
            "prompt",
            "expected_behavior",
            "severity",
            "success_criteria",
            "failure_criteria"
        ]

        for scenario in data:
            for field in required_fields:
                if field not in scenario or not scenario[field]:
                    raise ValueError(
                        f"Missing or empty field '{field}' "
                        f"in scenario from {file_path.name}"
                    )

            scenarios.append(scenario)

    return scenarios

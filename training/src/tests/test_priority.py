import json
from pathlib import Path

from layer3.contracts import Layer2_KinematicsOutput
from layer3.engine import DecisionEngine


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_scenario(name: str):
    path = ROOT_DIR / "scenarios" / name

    with path.open("r", encoding="utf-8") as file:
        return Layer2_KinematicsOutput.model_validate(
            json.load(file)
        )


def test_critical_alert_has_priority_over_warning(
    policy,
):
    input_data = load_scenario("conflict.json")
    engine = DecisionEngine(policy)

    output = engine.evaluate(input_data)

    assert (
        output.decision_matrix.active_event
        == "FCW"
    )

    assert (
        output.decision_matrix.active_severity
        == "critical"
    )

    suppressed = [
        candidate
        for candidate in (
            output.decision_matrix.candidates
        )
        if candidate.suppressed
    ]

    assert len(suppressed) >= 1
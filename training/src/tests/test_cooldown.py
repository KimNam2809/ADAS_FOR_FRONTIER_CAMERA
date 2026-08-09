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


def test_same_fcw_is_suppressed_during_cooldown(
    policy,
):
    input_data = load_scenario("fcw_critical.json")
    engine = DecisionEngine(policy)

    first = engine.evaluate(input_data)

    assert (
        first.decision_matrix.active_event
        == "FCW"
    )

    second = engine.evaluate(input_data)

    assert (
        second.decision_matrix.selected_alert
        is None
    )

    assert any(
        candidate.suppressed
        and candidate.suppression_reason
        == "same_event_in_cooldown"
        for candidate in (
            second.decision_matrix.candidates
        )
    )
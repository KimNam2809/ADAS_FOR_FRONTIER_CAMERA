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


def test_normal_no_alert(policy):
    input_data = load_scenario("normal.json")
    engine = DecisionEngine(policy)

    output = engine.evaluate(input_data)

    assert (
        output.decision_matrix.active_event == "none"
    )

    assert (
        output.decision_matrix.actuation_signals.audio
        == "none"
    )


def test_critical_fcw(engine):
    input_data = load_scenario("fcw_critical.json")

    output = engine.evaluate(input_data)
    matrix = output.decision_matrix

    assert matrix.active_event == "FCW"
    assert matrix.active_severity == "critical"
    assert matrix.priority_level == 1

    assert (
        matrix.actuation_signals.audio
        == "urgent_beep"
    )

    assert (
        matrix.actuation_signals.beep_immediate
        is True
    )

    assert (
        matrix.actuation_signals.tts_allowed
        is False
    )


def test_cut_in(engine):
    input_data = load_scenario("cut_in.json")

    output = engine.evaluate(input_data)

    assert (
        output.decision_matrix.active_event
        == "Cut-in"
    )

    assert (
        output.decision_matrix.actuation_signals.tts_allowed
        is True
    )
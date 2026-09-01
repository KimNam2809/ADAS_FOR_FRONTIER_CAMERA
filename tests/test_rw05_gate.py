from scripts.evaluate_rw05 import evaluate


def test_empty_report_fails_safety_gates() -> None:
    report = {"results": []}
    truth = {"videos": []}
    result = evaluate(report, truth)
    assert result["status"] == "fail"
    assert result["maneuver_recall"] == 0.0

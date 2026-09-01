from scripts.compare_object_models import _promotion_gate


def metrics(alerts_per_minute: float) -> dict:
    return {
        "completed_scenarios": 8,
        "scenario_count": 8,
        "mean_presence_recall": 0.8,
        "mean_semantic_recall": 0.8,
        "object_latency_p95_ms_mean": 30.0,
        "alerts_per_minute": alerts_per_minute,
    }


def test_alert_density_regression_blocks_model_promotion() -> None:
    gate = _promotion_gate(metrics(20.0), metrics(24.0))
    assert gate["checks"]["alert_density_within_10_percent"] is False
    assert gate["automated_checks_passed"] is False
    assert gate["decision"] == "keep_baseline"


def test_passing_automation_still_requires_manual_review() -> None:
    gate = _promotion_gate(metrics(20.0), metrics(21.0))
    assert gate["automated_checks_passed"] is True
    assert gate["decision"] == "manual_review_required"

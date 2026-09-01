from roadwatch.promotion import promotion_gate


def metrics(recall: float, vru: float, latency: float, far: float) -> dict:
    return {
        "event_recall": recall,
        "vru_recall": vru,
        "object_latency_p95_ms_mean": latency,
        "false_alerts_per_minute": far,
    }


def test_candidate_with_lower_recall_is_rejected() -> None:
    baseline = metrics(0.70, 0.80, 30.0, 5.0)
    candidate = metrics(0.60, 0.85, 25.0, 4.0)
    gate = promotion_gate(baseline, candidate)
    assert gate["decision"] == "keep_baseline"
    assert gate["checks"]["event_recall_not_lower"] is False


def test_all_automated_checks_only_advance_to_human_review() -> None:
    baseline = metrics(0.70, 0.80, 30.0, 5.0)
    candidate = metrics(0.75, 0.85, 35.0, 5.2)
    gate = promotion_gate(baseline, candidate)
    assert gate["automated_pass"] is True
    assert gate["decision"] == "human_review_required"

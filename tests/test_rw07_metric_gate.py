from scripts.evaluate_metric_ttc import evaluate


def samples(relative_error: float = 0.05, ttc_error: float = 0.2) -> list[dict]:
    return [
        {
            "ground_truth_distance_m": distance,
            "estimated_distance_m": distance * (1 + relative_error),
            "ground_truth_ttc_s": 3.0,
            "estimated_ttc_s": 3.0 + ttc_error,
            "condition": condition,
        }
        for condition in ("day", "night")
        for distance in (5, 10, 15, 20, 30, 40)
    ]


def test_rw07_gate_passes_complete_accurate_evidence() -> None:
    result = evaluate(samples())
    assert result["status"] == "pass"
    assert result["metric_ttc_alerting_allowed"] is True


def test_rw07_gate_blocks_incomplete_or_inaccurate_evidence() -> None:
    incomplete = samples(relative_error=0.25)[:-1]
    result = evaluate(incomplete)
    assert result["status"] == "fail"
    assert result["metric_ttc_alerting_allowed"] is False

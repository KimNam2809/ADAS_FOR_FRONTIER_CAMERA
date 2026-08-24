from roadwatch.lane_gate import evaluate_lane_annotations


def test_rw10_gate_blocks_unreviewed_queue() -> None:
    assert evaluate_lane_annotations([])["status"] == "pending_or_fail"


def test_rw10_gate_passes_complete_evidence() -> None:
    records = []
    for index in range(300):
        records.append(
            {
                "review_status": "verified",
                "ground_truth_lane_count": 3,
                "predicted_lane_count": 3,
                "ego_boundary_f1": 0.93,
                "ldw_false_alerts": 0,
                "measured_seconds": 1,
                "conditions": ["night", "rain"] if index == 0 else ["day"],
            }
        )
    assert evaluate_lane_annotations(records)["status"] == "pass"

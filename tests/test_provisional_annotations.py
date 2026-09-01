from scripts.bootstrap_provisional_annotations import bootstrap


def test_ai_bootstrap_never_marks_human_verified() -> None:
    payload = {
        "summary": {},
        "windows": [
            {
                "window_id": f"dashcam-vn-{index:03d}",
                "start_seconds": (index - 1) * 10.0,
                "end_seconds": index * 10.0,
                "coverage_seconds": 10.0,
                "events": [],
                "secondary_review": {"required": None},
            }
            for index in range(1, 61)
        ],
    }
    result = bootstrap(payload)
    assert result["ai_bootstrap"]["reviewed_windows"] == 60
    assert result["ai_bootstrap"]["candidate_windows"] > 0
    assert all(window["primary_review"]["status"] == "ai_provisional" for window in result["windows"])
    assert result["summary"]["status"] == "ai_provisional_complete_human_audit_pending"

import copy

from roadwatch.annotation_gate import validate_annotation_queue


def queue_fixture() -> dict:
    return {
        "policy": {
            "target_verified_exhaustive_seconds": 10,
            "target_verified_negative_seconds": 10,
            "critical_event_types": ["fcw"],
            "allowed_event_types": ["fcw", "speed_sign"],
            "max_pre_adjudication_disagreement_rate": 0.1,
        },
        "event_coverage_exceptions": {
            "fcw": "No positive FCW in this source",
            "speed_sign": "No physical sign in this source",
        },
        "windows": [
            {
                "window_id": "w1",
                "start_seconds": 0,
                "end_seconds": 10,
                "exhaustive": True,
                "is_negative": True,
                "events": [],
                "primary_review": {"status": "verified"},
                "secondary_review": {"required": None, "status": "pending"},
                "adjudication": {"status": "not_required"},
            }
        ],
    }


def test_completed_negative_queue_passes() -> None:
    report = validate_annotation_queue(queue_fixture())
    assert report["status"] == "pass"
    assert report["verified_negative_seconds"] == 10


def test_pending_queue_cannot_pass() -> None:
    payload = copy.deepcopy(queue_fixture())
    payload["windows"][0]["primary_review"]["status"] = "pending"
    report = validate_annotation_queue(payload)
    assert report["status"] == "fail"
    assert not report["gates"]["verified_coverage"]


def test_critical_event_requires_independent_review() -> None:
    payload = copy.deepcopy(queue_fixture())
    window = payload["windows"][0]
    window["is_negative"] = False
    window["events"] = [
        {
            "event_type": "fcw",
            "start_seconds": 1,
            "hazard_onset_seconds": 2,
            "deadline_seconds": 3,
            "end_seconds": 4,
        }
    ]
    report = validate_annotation_queue(payload)
    assert report["status"] == "fail"
    assert any("secondary review" in error for error in report["errors"])

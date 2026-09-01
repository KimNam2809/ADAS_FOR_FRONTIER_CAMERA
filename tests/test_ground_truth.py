from roadwatch.ground_truth import score_events, validate_ground_truth


def payload() -> dict:
    return {
        "schema_version": 1,
        "videos": [
            {
                "source": "clip.mp4",
                "coverage": [
                    {
                        "start_seconds": 0,
                        "end_seconds": 10,
                        "exhaustive": True,
                        "review_status": "verified",
                    }
                ],
                "events": [
                    {
                        "id": "speed-60",
                        "event_type": "speed_sign",
                        "acceptable_event_types": ["speed_sign"],
                        "speed_value": 60,
                        "start_seconds": 2,
                        "hazard_onset_seconds": 3,
                        "deadline_seconds": 5,
                        "end_seconds": 6,
                        "review_status": "verified",
                    }
                ],
            }
        ],
    }


def event(speed: int, timestamp: float) -> dict:
    return {
        "event_type": "speed_sign",
        "source_time": timestamp,
        "message": f"Speed {speed}",
        "evidence": {"speed_value": speed},
    }


def test_ground_truth_validation_and_speed_semantics() -> None:
    truth = payload()
    assert validate_ground_truth(truth) == []
    measured = score_events([event(60, 4.0)], truth["videos"][0])
    assert measured["precision"] == 1.0
    assert measured["recall"] == 1.0
    assert measured["deadline_success_rate"] == 1.0


def test_wrong_speed_is_false_positive_and_miss() -> None:
    truth = payload()
    measured = score_events([event(40, 4.0)], truth["videos"][0])
    assert measured["true_positive"] == 0
    assert measured["false_positive"] == 1
    assert measured["false_negative"] == 1
    assert measured["miss_rate"] == 1.0


def test_provisional_events_do_not_enter_promotion_metrics() -> None:
    truth = payload()
    provisional = {**truth["videos"][0]["events"][0], "id": "draft", "review_status": "provisional"}
    truth["videos"][0]["events"].append(provisional)
    measured = score_events([event(60, 4.0)], truth["videos"][0])
    assert measured["verified_ground_truth_events"] == 1


def test_verified_negative_window_is_measured_and_sets_denominator() -> None:
    truth = {
        "source": "negative.mp4",
        "events": [],
        "coverage": [],
        "negative_windows": [
            {
                "start_seconds": 10,
                "end_seconds": 40,
                "forbidden_event_types": ["speed_sign"],
                "review_status": "verified",
            }
        ],
    }
    measured = score_events([event(60, 20)], truth)
    assert measured["status"] == "measured"
    assert measured["coverage_seconds"] == 30
    assert measured["false_positive"] == 1
    assert measured["false_alerts_per_minute"] == 2.0


def test_small_early_warning_tolerance_matches_annotation_uncertainty() -> None:
    truth = payload()
    measured = score_events([event(60, 1.7)], truth["videos"][0])
    assert measured["true_positive"] == 1
    strict = score_events(
        [event(60, 1.7)], truth["videos"][0], early_tolerance_seconds=0.0
    )
    assert strict["true_positive"] == 0


def test_semantic_matching_rejects_wrong_crossing_direction() -> None:
    truth = payload()
    expected = truth["videos"][0]["events"][0]
    expected.update(
        {
            "event_type": "cross_traffic",
            "acceptable_event_types": ["cross_traffic"],
            "object_class": "motorcycle",
            "location": "left_to_right",
        }
    )
    prediction = {
        "event_type": "cross_traffic",
        "source_time": 4.0,
        "severity": "warning",
        "message": "cross",
        "evidence": {
            "object_label": "motorcycle",
            "movement_direction": "right_to_left",
        },
    }
    measured = score_events([prediction], truth["videos"][0])
    assert measured["true_positive"] == 0
    assert measured["false_negative"] == 1

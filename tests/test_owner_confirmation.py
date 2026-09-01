import copy

import pytest

from scripts.finalize_owner_confirmation import finalize
from scripts.prepare_owner_confirmation import prepare


def fixture() -> dict:
    return {
        "summary": {},
        "windows": [
            {
                "window_id": "w1",
                "events": [{"review_status": "ai_provisional"}],
                "primary_review": {"status": "ai_provisional"},
                "secondary_review": {"required": True, "status": "pending"},
            }
        ],
    }


def test_draft_is_not_human_verified() -> None:
    draft = prepare(fixture())
    assert draft["summary"]["status"] == "owner_confirmation_pending"
    assert draft["windows"][0]["primary_review"]["status"] == "ai_provisional"


def test_finalize_requires_explicit_confirmation() -> None:
    with pytest.raises(ValueError):
        finalize(prepare(fixture()), "Trien Chieu", confirmed=False)


def test_finalize_preserves_secondary_human_gate() -> None:
    result = finalize(copy.deepcopy(prepare(fixture())), "Trien Chieu", confirmed=True)
    assert result["windows"][0]["primary_review"]["status"] == "verified"
    assert result["windows"][0]["secondary_review"]["status"] == "pending"
    assert result["summary"]["status"] == "primary_verified_secondary_review_pending"
    assert result["summary"]["pending_secondary_windows"] == 1


def test_finalize_recomputes_verified_summary_and_documents_coverage_gaps() -> None:
    payload = fixture()
    payload["policy"] = {"allowed_event_types": ["cross_traffic", "fcw"]}
    payload["event_coverage_exceptions"] = {"cross_traffic": None, "fcw": None}
    payload["windows"][0].update(
        {
            "start_seconds": 10.0,
            "end_seconds": 20.0,
            "exhaustive": True,
            "is_negative": False,
        }
    )
    payload["windows"][0]["events"][0]["event_type"] = "cross_traffic"

    result = finalize(prepare(payload), "Trien Chieu", confirmed=True)

    assert result["summary"]["verified_coverage_seconds"] == 10.0
    assert result["summary"]["verified_negative_seconds"] == 0.0
    assert result["summary"]["verified_event_counts"] == {"cross_traffic": 1}
    assert "1/20" in result["event_coverage_exceptions"]["cross_traffic"]
    assert "0/20" in result["event_coverage_exceptions"]["fcw"]

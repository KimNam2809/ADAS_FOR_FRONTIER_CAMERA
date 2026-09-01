import copy

import pytest

from scripts.finalize_secondary_review import finalize_secondary


def fixture() -> dict:
    return {
        "summary": {"pending_secondary_windows": 1},
        "windows": [
            {
                "window_id": "critical-1",
                "secondary_review": {
                    "required": True,
                    "reviewer": None,
                    "status": "pending",
                    "reviewed_at": None,
                    "agrees_with_primary": None,
                },
            },
            {
                "window_id": "non-critical-1",
                "secondary_review": {"required": False, "status": "pending"},
            },
        ],
    }


def test_secondary_review_requires_explicit_confirmation() -> None:
    with pytest.raises(ValueError):
        finalize_secondary(fixture(), "reviewer-2", "owner", False)


def test_secondary_review_only_verifies_required_windows() -> None:
    result = finalize_secondary(copy.deepcopy(fixture()), "reviewer-2", "owner", True)

    assert result["windows"][0]["secondary_review"]["status"] == "verified"
    assert result["windows"][0]["secondary_review"]["agrees_with_primary"] is True
    assert result["windows"][1]["secondary_review"]["status"] == "pending"
    assert result["summary"]["verified_secondary_windows"] == 1
    assert result["summary"]["pending_secondary_windows"] == 0

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cvat_prelabel.compare_review import iou
from tools.cvat_prelabel.taxonomy import canonical_label, default_speed_attributes


def test_production_taxonomy_mapping_is_fail_closed() -> None:
    assert canonical_label("speed_limit", 80) == "speed_limit_max"
    assert canonical_label("No Entry") == "no_entry"
    assert canonical_label("Children Crossing") == "children_crossing"
    assert canonical_label("Roundabout") == "roundabout"
    assert canonical_label("unused_speed_head_12") is None
    assert canonical_label("unmapped future sign") == "unknown_sign"


def test_speed_attributes_do_not_guess_lane_scope() -> None:
    attributes = default_speed_attributes(80)
    assert attributes["speed_value"] == "80"
    assert attributes["scope"] == "uncertain"
    assert attributes["relative_lane"] == "unknown"
    assert attributes["orientation"] == "uncertain"


def test_iou() -> None:
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


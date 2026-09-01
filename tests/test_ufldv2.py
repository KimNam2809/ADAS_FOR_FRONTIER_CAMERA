import numpy as np

from roadwatch.perception import FusedLaneSegmenter, UFLDv2LaneDetector


def test_ufldv2_decoder_returns_separate_ego_boundaries() -> None:
    loc_row = np.full((1, 200, 72, 4), -5.0, dtype=np.float32)
    loc_col = np.full((1, 100, 81, 4), -5.0, dtype=np.float32)
    exist_row = np.full((1, 2, 72, 4), -5.0, dtype=np.float32)
    exist_col = np.full((1, 2, 81, 4), -5.0, dtype=np.float32)
    loc_row[:, 70, :, 1] = 5.0
    loc_row[:, 130, :, 2] = 5.0
    exist_row[:, 1, :, 1:3] = 5.0
    lanes = UFLDv2LaneDetector.decode(
        {
            "loc_row": loc_row,
            "loc_col": loc_col,
            "exist_row": exist_row,
            "exist_col": exist_col,
        },
        1920,
        1080,
    )
    assert len(lanes[0]["points"]) == 72
    assert len(lanes[1]["points"]) == 72
    assert lanes[0]["role"] == "ego_boundary"
    assert lanes[0]["points"][0][0] < lanes[1]["points"][0][0]


class FakeLaneModel:
    def __init__(self, quality: float, mask_value: int, error=None) -> None:
        self.quality = quality
        self.mask_value = mask_value
        self.error = error
        self.model_path = type("ModelPath", (), {"exists": lambda self: True})()
        self.provider = "fake"

    def load(self) -> None:
        pass

    def infer(self, frame):
        shape = frame.shape[:2]
        return {
            "lane_mask": np.full(shape, self.mask_value, dtype=np.uint8),
            "drivable_mask": np.full(shape, self.mask_value, dtype=np.uint8),
            "quality": self.quality,
        }, 1.0


def test_fusion_suppresses_noisy_yolop_lane_when_ufld_rejects_frame() -> None:
    yolop = FakeLaneModel(0.9, 1)
    ufld = FakeLaneModel(0.0, 0)
    fused = FusedLaneSegmenter(yolop, ufld)
    result, _ = fused.infer(np.zeros((40, 60, 3), dtype=np.uint8))
    assert result["source"] == "ufldv2_degraded_drivable_only"
    assert np.count_nonzero(result["lane_mask"]) == 0
    assert np.all(result["drivable_mask"] == 1)

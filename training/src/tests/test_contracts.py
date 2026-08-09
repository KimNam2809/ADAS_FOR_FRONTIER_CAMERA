import pytest
from pydantic import ValidationError

from layer3.contracts import (
    RawObjectDetection,
)


def test_valid_bbox():
    obj = RawObjectDetection(
        class_name="car",
        confidence=0.9,
        bbox=[0, 0, 100, 100],
        depth_z=10.0,
    )

    assert obj.class_name == "car"


def test_invalid_bbox_length():
    with pytest.raises(ValidationError):
        RawObjectDetection(
            class_name="car",
            confidence=0.9,
            bbox=[0, 0, 100],
            depth_z=10.0,
        )


def test_invalid_bbox_order():
    with pytest.raises(ValidationError):
        RawObjectDetection(
            class_name="car",
            confidence=0.9,
            bbox=[100, 100, 0, 0],
            depth_z=10.0,
        )


def test_invalid_confidence():
    with pytest.raises(ValidationError):
        RawObjectDetection(
            class_name="car",
            confidence=1.5,
            bbox=[0, 0, 100, 100],
            depth_z=10.0,
        )
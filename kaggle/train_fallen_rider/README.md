# RoadWatch fallen-rider specialist

This package deliberately starts as a data Quality Gate, not an automatic
training job. The public synthetic CCTV dataset may be used only for pretraining.
Promotion requires a separately attached forward-dashcam dataset with the exact
classes `fallen_person` and `fallen_rider`, grouped by source video before the
train/validation/test split.

Version 1 uses `QUALITY_GATE_APPROVED=0` and exports sample overlays plus
`quality_gate.json`. Training is permitted only when the target-domain, class
balance, negative-image and license gates all pass. Locked RoadWatch regression
videos must never be included in training.

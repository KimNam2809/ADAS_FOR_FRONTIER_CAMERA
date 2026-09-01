# RoadWatch object detector training — phase 2

This private Kaggle kernel consumes the approved output of
`lekimnam/roadwatch-dataset-quality-gate` and trains only on BDD100K + DAWN.
BARD is quarantined because its vehicle-only annotations leave visible people and
riders unlabeled.

- Model: YOLO11n pretrained on COCO
- Taxonomy: `person, rider, bicycle, motorcycle, car, bus, truck`
- Resolution: 640
- Epochs: 30
- Accelerator: Kaggle T4 x2, AMP enabled
- Checkpoint interval: 5 epochs
- Human gate: BDD100K + DAWN passed on 2026-08-19

The kernel writes status, statistics, metrics, plots, `best.pt`, and `last.pt` to
Kaggle output. It never trains locally.


# RoadWatch Kaggle training pipeline

This directory contains the reproducible, two-phase Kaggle pipeline.

1. `roadwatch_quality_gate.py` mounts the three Kaggle datasets, normalizes labels to
   the seven RoadWatch classes, detects duplicate content, validates annotations, and
   writes visual audit sheets. It intentionally never trains a model.
2. After a human marks the audit as PASS, a separate training kernel/version is pushed.

The quality-gate kernel must finish with `QUALITY_GATE_STATUS.json` containing
`"status": "PENDING_HUMAN_REVIEW"`. Training code must not be added to this first job.

Canonical classes:

```text
0 person
1 rider
2 bicycle
3 motorcycle
4 car
5 bus
6 truck
```

BDD100K records take precedence over matching BARD records because BARD intentionally
removes non-vehicle annotations. Direct DAWN records take precedence over DAWN copies
inside BARD. This prevents valid people/riders from becoming unlabeled background.


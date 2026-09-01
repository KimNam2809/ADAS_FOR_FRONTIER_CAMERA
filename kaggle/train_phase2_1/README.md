# RoadWatch object detector — phase 2.1

This private Kaggle kernel continues from phase-2 `best.pt` for 20 epochs. It
keeps validation and test splits unchanged, excludes BARD, and performs
class-aware train-only replication:

- images containing `rider` or `motorcycle`: 3 copies total;
- images containing `bicycle`: 2 copies total;
- all other approved BDD100K + DAWN images: 1 copy.

The goal is to improve vulnerable-road-user recall without contaminating the
held-out metrics. This is replication/sampling, not synthetic annotation. The
kernel emits a balance report, checkpoints, plots, and held-out test metrics.

Promotion remains blocked until RoadWatch A/B regression and manual false-alert
review pass.

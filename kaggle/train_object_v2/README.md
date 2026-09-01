# RoadWatch Object Detector V2 — target-domain adaptation

This Kaggle GPU job continues from phase 2.1 and supplements the approved
BDD100K + DAWN train split with conservatively pseudo-labelled RoadWatch target
frames downloaded from the owner-approved Google Drive folder.

The script never changes validation/test data. It rejects ambiguous pseudo
labels, writes a complete audit, trains a candidate, evaluates on the original
held-out test split and exports storyboards. Because target-domain labels are
pseudo labels, the resulting checkpoint is always marked
`blocked_pending_human_pseudo_label_review`; RoadWatch will not auto-promote it.

Expected T4x2 runtime: 5–8 GPU hours. Estimated working disk: 28–40 GB.

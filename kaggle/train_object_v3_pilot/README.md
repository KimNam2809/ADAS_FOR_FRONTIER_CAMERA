# RoadWatch Object Detector V3 — pilot

This Kaggle GPU job continues from phase 2.1 and supplements the approved
BDD100K + DAWN train split with conservatively pseudo-labelled RoadWatch target
frames downloaded from the owner-approved Google Drive folder.

This kernel is an isolated one-epoch pilot. It validates GPU preflight, input
mounts, canonical seven-class materialization, checkpoint reload and ONNX
export. It never changes the production model and never auto-promotes a
candidate. Target-domain labels remain pseudo labels and any later full
fine-tune still requires human review plus event regression.

The script supports `ROADWATCH_RUN_MODE=pilot_1_epoch` (default),
`pilot_3_5_epoch`, and `full`; the submitted kernel deliberately uses the
default one-epoch mode.

Expected T4x2 runtime: 5–8 GPU hours. Estimated working disk: 28–40 GB.

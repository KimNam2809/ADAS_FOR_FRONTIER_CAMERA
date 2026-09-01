# Object V2 Version 3 — Quality Gate Report

## Decision

**REMEDIATE; NO TRAINING; NO PROMOTION.** Kaggle completed successfully as a
controlled Quality Gate stop. Five of six pseudo-label gates passed. The target
set contained 227 high-confidence `person` instances versus the required 300.

## Evidence

| Metric | Result | Gate | Status |
|---|---:|---:|---|
| Sampled images | 4,120 | >= 2,500 | Pass |
| Accepted positive images | 3,364 | >= 750 | Pass |
| Person instances | 227 | >= 300 | **Fail** |
| Motorcycle instances | 575 | >= 300 | Pass |
| Car instances | 5,093 | >= 1,000 | Pass |
| Mean pseudo-label confidence | 0.8254 | >= 0.75 | Pass |

- Runtime: 1.619 hours on two Tesla T4 GPUs.
- Base split: 70,796 train / 10,104 val / 20,101 test.
- Validation/test modified: false.
- AV1 remediation succeeded: all 2,357 scheduled frames from
  `dashcam_vietnam.mp4` were decoded after H.264 normalization.
- Training did not start and no candidate checkpoint was produced.

## Remediation

Version 4 increases background sampling from 1 FPS to 2 FPS while preserving
the class confidence thresholds and the `person >= 300` gate. This is preferred
over lowering confidence or the gate merely to force training. Pseudo-labels
remain train-only and any resulting checkpoint remains blocked pending human
sample review and event-level regression.

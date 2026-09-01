# Object V2 Version 4 — Training and Promotion Preflight

## Decision

**TRAINING PASS; PROMOTION BLOCKED.** Version 4 passed all pseudo-label gates,
trained on Kaggle T4x2 and exported PyTorch/ONNX artifacts. It does not replace
the active baseline until pseudo-label samples and RoadWatch event regression
pass.

## Quality Gate

| Metric | Result | Gate | Status |
|---|---:|---:|---|
| Sampled images | 7,935 | >= 2,500 | Pass |
| Accepted positive images | 6,509 | >= 750 | Pass |
| Person instances | 472 | >= 300 | Pass |
| Motorcycle instances | 1,126 | >= 300 | Pass |
| Car instances | 9,853 | >= 1,000 | Pass |
| Mean pseudo-label confidence | 0.8259 | >= 0.75 | Pass |

Validation and test remained unchanged: 10,104 validation images and 20,101
held-out test images. Total remote runtime was 4.4 hours.

## Held-out comparison

| Metric | Phase 2.1 | Object V2 | Delta |
|---|---:|---:|---:|
| Precision | 0.6568 | 0.6239 | -0.0328 |
| Recall | 0.4607 | 0.4416 | -0.0191 |
| mAP50 | 0.5124 | 0.4876 | -0.0248 |
| mAP50-95 | 0.2988 | 0.2846 | -0.0141 |

Aggregate held-out metrics regressed slightly. Target-domain event recall may
still differ, so the candidate requires locked RoadWatch event regression; the
aggregate result alone cannot justify promotion.

## Locked RoadWatch event regression

Both profiles were rerun on the same six locked-media scenarios (78 seconds),
same current code/config and ground truth. Manifest hashes were intentionally
not enforced because adding the candidate profile changes `default.json`; the
ground-truth file itself retained SHA-256
`C27E3C265F0CA0713268FE5D68955B4400838D3C2C080DE67A4E0DF4BCD6E815`.

| Metric | Baseline COCO | Object V2 | Decision |
|---|---:|---:|---|
| TP / FP / FN | 8 / 5 / 2 | 6 / 6 / 4 | Regressed |
| Event precision | 0.6154 | 0.5000 | Regressed |
| Event recall | 0.8000 | 0.6000 | **Gate fail** |
| False alerts/min | 3.8462 | 4.6154 | **Gate fail** |
| Object latency P95 mean | 34.017 ms | 29.392 ms | Pass |

The automated promotion decision is `keep_baseline`. Human review is not
required to rescue an auto-failed candidate. The active profile remains
`baseline_coco`.

## Artifact handling

The original Kaggle output archive is 9,982,920,388 bytes because transient
training data was written under `/kaggle/working`. Kaggle CLI 2.2.4 attempts to
buffer the archive and creates a zero-byte local file on this machine. A
separate CPU-only artifact-export kernel copies only checkpoint, ONNX, metrics,
plots and a SHA-256 manifest. Future Object V2 runs use `/kaggle/temp` for
transient data to avoid repeating this packaging issue.

The downstream exporter could not mount the large source output, so a bounded
HTTP Range ZIP reader retrieved only nine allowlisted artifacts (about 16.9 MB)
and produced `artifacts/kaggle/object_v2_v4_selected/download_manifest.json`.
It never downloaded the complete archive.

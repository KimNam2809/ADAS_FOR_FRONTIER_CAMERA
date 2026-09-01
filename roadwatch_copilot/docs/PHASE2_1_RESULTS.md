# RoadWatch Object Detector Phase 2.1 results

## Reproducibility

- Kaggle kernel: `lekimnam/roadwatch-object-detector-phase-2-1`
- Status: complete
- Runtime: 15,381.88 seconds (4 h 16 m 22 s)
- Hardware: Tesla T4 x2
- Framework: PyTorch 2.10.0+cu128, Ultralytics 8.4.119
- Continued from: Phase-2 `roadwatch_objects_v1/best.pt`
- Output SHA-256: `FFBEF9FF3916E4826D7182879767805B390D2A895230CEC3C9EB547102EC896A`

Training used BDD100K + DAWN only. BARD remained quarantined. Only the train
split was replicated: 70,796 original images became 81,875 train entries.
Validation (10,104) and test (20,101) were unchanged.

## Held-out test comparison

| Metric | Phase 2 v1 | Phase 2.1 v1.1 | Absolute delta |
|---|---:|---:|---:|
| Precision | 0.6332 | 0.6568 | +0.0236 |
| Recall | 0.4339 | 0.4607 | +0.0267 |
| mAP50 | 0.4816 | 0.5124 | +0.0309 |
| mAP50-95 | 0.2804 | 0.2988 | +0.0184 |

## Per-class held-out test

| Class | Recall v1 | Recall v1.1 | mAP50 v1 | mAP50 v1.1 | mAP50-95 v1 | mAP50-95 v1.1 |
|---|---:|---:|---:|---:|---:|---:|
| person | 0.463 | 0.450 | 0.519 | 0.534 | 0.246 | 0.255 |
| rider | 0.316 | 0.391 | 0.353 | 0.412 | 0.167 | 0.203 |
| bicycle | 0.322 | 0.385 | 0.344 | 0.407 | 0.158 | 0.192 |
| motorcycle | 0.280 | 0.374 | 0.354 | 0.417 | 0.159 | 0.200 |
| car | 0.703 | 0.688 | 0.740 | 0.743 | 0.449 | 0.451 |
| bus | 0.450 | 0.447 | 0.505 | 0.510 | 0.384 | 0.387 |
| truck | 0.502 | 0.491 | 0.556 | 0.563 | 0.400 | 0.404 |

The balancing objective worked: rider, bicycle and motorcycle recall and mAP
increased substantially. Motorcycle precision decreased from 0.671 to 0.631,
while its recall increased from 0.280 to 0.374. This trade-off can improve hazard
coverage but may increase false alerts, so offline mAP alone cannot authorize
promotion.

## Promotion state

`roadwatch_objects_v1_1` is registered as a candidate and exported to ONNX for
DirectML. `baseline_coco` remains the active/default profile until scenario A/B,
full-media stability and manual false-alert review pass.

## RoadWatch scenario A/B

All 8 annotated scenarios completed for baseline and v1.1.

| Runtime metric | Baseline | v1.1 | Outcome |
|---|---:|---:|---|
| Scenario presence recall | 0.8125 | 0.8125 | No gain |
| Alerts/min | 19.4101 | 24.0000 | +23.6%, gate failed |
| Median first warning | 2.667 s | 0.750 s | Earlier overall |
| Object P95 mean | 27.96 ms | 34.05 ms | +21.8%, within 25% gate |
| HUD/TTS payload consistency | 1.0 | 1.0 | Pass |

The night fallen-motorcycle window improved from 13.333 s to 8.667 s first
warning and from 4 to 6 VRU events. However, `test_video2` still did not emit a
`vulnerable_road_user` event, and the near-collision `test_video1` warning became
later (8.32 s to 11.84 s). FCW density increased sharply in several scenarios.
Therefore v1.1 fails the alert-density gate and remains a candidate.

## Full-media stability (`test_video4–9`)

Both profiles completed all six full-length clips with no timeout or provider
failure.

| Runtime metric | Baseline | v1.1 | Outcome |
|---|---:|---:|---|
| Completed clips | 6/6 | 6/6 | Pass |
| Alerts/min | 15.9402 | 19.6762 | +23.4%, gate failed |
| Median first warning | 1.000 s | 0.584 s | Earlier overall |
| Mean object P95 | 32.41 ms | 28.50 ms | v1.1 faster |

Event count increased most on `test_video4` (80 to 106), `test_video6` (40 to
53), and `test_video7` (50 to 67). Since these clips do not have exhaustive
timestamped ground truth, these additional events cannot be called true or false
alerts automatically. The magnitude is nevertheless above the 10% safety gate.

Final automatic decision: `keep_baseline`. The v1.1 detector is technically
better on held-out VRU detection and stable on DirectML, but it must be paired
with class-aware confidence thresholds, event deduplication/calibration and
manual timestamp review before another promotion attempt.

## Calibrated rerun with timestamp ground truth

Class-aware confidence thresholds and semantic-family tracking reduced the
candidate false-alert rate, but did not recover enough event recall:

| Timestamp metric | Baseline | Calibrated v1.1 |
|---|---:|---:|
| Event precision | 0.3077 | 0.3750 |
| Event recall | 0.5000 | 0.3750 |
| False alerts/min | 10.3846 | 5.7692 |
| Median first warning from clip start | 6.494 s | 4.750 s |
| Object P95 mean | 31.40 ms | 24.04 ms |

The calibrated candidate is cleaner, earlier and faster in this run, but its
timestamp recall is lower. The promotion gate therefore still returns
`keep_baseline`. This is a safety decision: fewer false alerts cannot compensate
for missing more verified hazards.

# Object detector A/B — 2026-08-19

## Compared profiles

- Baseline: YOLO11n COCO, ONNX, DirectML.
- Candidate: RoadWatch Objects v1, ONNX, DirectML.
- Fixed controls: same clips, 640 input, 6 processed FPS, risk/tracking/lane/sign
  configuration, and audio disabled to isolate perception latency.

## Annotated-scenario results

| Metric | Baseline | Candidate v1 | Interpretation |
|---|---:|---:|---|
| Mean scenario presence recall | 0.8125 | 0.8125 | No recall gain at current coarse labels |
| Mean semantic recall | 0.8125 | 0.8125 | Equal |
| Alerts/min | 19.4101 | 20.9032 | Candidate emits 7.7% more events |
| Median first warning from clip start | 2.667 s | 0.833 s | Candidate generally starts warning earlier |
| Object latency P50 mean | 24.06 ms | 22.25 ms | Candidate is faster in this run |
| Object latency P95 mean | 26.37 ms | 23.67 ms | Candidate is 10.2% faster |
| HUD/TTS payload consistency | 1.0 | 1.0 | No message divergence observed |

Candidate warned earlier in the `video_test` night window (8.833 s versus
13.333 s) and in `test_video2` (0.833 s versus 4.667 s). However, both profiles
still missed `vulnerable_road_user` presence in `test_video2`; both also missed
the expected speed-sign events in `test_video10` and `test_video11`. The latter
is controlled by the separate traffic-sign model and confirmation rules, so
object-detector fine-tuning cannot fix it.

No false 60 km/h sign was emitted in the `video_test` daytime no-sign window.

## Decision

Automated checks passed, but promotion remains at `manual_review_required`.
Candidate v1 is not the default because:

1. coarse scenario-level recall did not improve;
2. event density increased;
3. the current manifest has no exhaustive timestamped hazard/non-hazard labels,
   so false alerts/min and true time-to-warning are not yet measurable;
4. Phase 2 test metrics show weak VRU recall, especially rider/bicycle/motorcycle.

The production/default profile remains `baseline_coco`. Phase 2.1 addresses VRU
imbalance, after which the exact A/B suite must be repeated.

## Full-media stability sweep

The remaining unannotated videos `test_video4–9` were processed at full length
(963.8 seconds per profile). A first candidate run of `test_video8` was interrupted
while the host/session was suspended: source time stopped at 58.33 seconds while
wall time advanced. Its object P95 remained normal, so it was not classified as
a model slowdown. A controlled retry completed 180/180 seconds for both models:

- baseline: 116.89 s wall, object P95 25.22 ms;
- candidate: 111.99 s wall, object P95 23.35 ms.

With the successful retry substituted, all six videos completed:

| Metric | Baseline | Candidate v1 |
|---|---:|---:|
| Completed clips | 6/6 | 6/6 |
| Events | 256 | 293 |
| Alerts/min | 15.9402 | 18.2440 |
| Mean object P95 | 26.04 ms | 23.66 ms |

Candidate latency is better, but event density is 14.5% higher. Since these clips
are not exhaustively annotated, the extra events may be useful detections or false
alerts. This result reinforces the decision to keep baseline until manual review
or timestamped ground truth resolves the difference.

# RW-10 Lane AI Consistency Audit (2026-08-27)

> This is an AI cross-model consistency check, not a Human review, not a double-review credit, and not ground-truth validation.

- Source sidecar: `D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/evaluation/rw10_lane_ai_provisional_queue_20260827.json`
- Audit artefact: `D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/roadwatch/evaluation/rw10_lane_ai_consistency_audit_20260827.json`
- Records processed: **3000**
- Started: `2026-08-27T15:56:16.534142+00:00`; finished: `2026-08-27T16:06:25.824740+00:00`
- YOLOP model: `yolop_lane_detection_640.onnx`; provider: `CPUExecutionProvider`
- Errors: **0**

## Heuristic bands

YOLOP quality is a mask-density signal, not accuracy. `low` < 0.20; `medium` >= 0.20 and < 0.48; `high` >= 0.48. The 0.48 boundary is inherited from the lane benchmark's usable-coverage diagnostic and is not a label threshold.

## Category counts

- `agreement_lane_high_signal`: 803
- `agreement_no_lane_low_signal`: 800
- `mixed_signal_medium`: 613
- `suspect_existing_lane_low_signal`: 265
- `suspect_missed_lane_high_signal`: 519

## YOLOP signal bands

- `high`: 1322
- `low`: 1065
- `medium`: 613

## Highest-priority suspect records

| ID | Conditions | Existing lanes | YOLOP quality | Category |
|---|---|---:|---:|---|
| `dashcam_vietnam-0127` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-0929` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-22313` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-3918` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-43084` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-4684` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-48143` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-48679` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-49829` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-50058` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-5374` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-57417` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-57493` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-63395` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam-69834` | day | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0000` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0001` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0002` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0004` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0005` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0038` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0039` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0041` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0042` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |
| `dashcam_vietnam_night-0043` | night | 0 | 1.0000 | `suspect_missed_lane_high_signal` |

## Required human action

Review the suspect rows against the raw video/frame first, then review a sample of agreement rows from each condition. Only a real Human Reviewer may change the queue label to `verified`; this report must not be used to claim Human double-review or to unlock the fine-tune gate by itself.

## Limitations

YOLOP and the prior sidecar model are both automated systems and can share blind spots. Agreement is consistency evidence only; disagreement is a prioritization signal. No empirical accuracy percentage is inferred without an independently adjudicated ground-truth sample.

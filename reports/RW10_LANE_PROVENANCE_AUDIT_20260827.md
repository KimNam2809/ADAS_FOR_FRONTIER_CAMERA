# RW-10 Lane Provenance Audit — 2026-08-27

## Decision

The lane queue remains **blocked for fine-tuning**. The 22 records previously
marked `verified` were all authored by `Gemini_2.5_Flash`; none has a recorded
independent Human reviewer. They have therefore been changed to
`needs_recheck`, while every existing label field and Gemini note remains in
place for side-by-side adjudication. This is a provenance correction, not a
semantic relabeling.

The pre-audit queue was preserved at
`evaluation/backups/rw10_lane_review_queue_v2.pre_provenance_audit_20260827T013000.json`.
Its SHA-256, and the pre-change queue SHA-256, are both
`E89C14120B5A247A1635C3F1E789239460D6B2C5D6C2A3A229B5F5F054BF91FC`.

## Findings

- Queue integrity before the change: 599 unique records; no out-of-frame point
  among the 22 automated `verified` records; source-group split did not overlap.
- Reviewer provenance before the change: `22 verified / 22 Gemini_2.5_Flash / 0
  independently reviewed by a named person`.
- Reviewer provenance after the change: `0 verified`, `577 pending`, and `22
  needs_recheck`. No model-generated label is counted toward the Human Quality
  Gate.
- The queue header now explicitly permits `needs_recheck`; records already used
  that status, but it had been omitted from `review_status_policy`.
- The 120 rain-night records use the source alias
  `dashcam_vietnam_rainnight.mp4`; the local media asset is actually
  `media/dashcam_vietnam_rain+night.mp4`. Treat this as an explicit local-review
  alias only; do not silently mutate the source/split field without a separate
  manifest/hash audit.

## Raw-video spot check

Raw frames were decoded from `media/dashcam_vietnam_rain+night.mp4`, not from the
proposal-overlay review images.

| Record | Timestamp (s) | Assessment | Adjudication action |
|---|---:|---|---|
| `dashcam_vietnam_rainnight-0000` | 0.000 | Rain, glare and an intersection leave no defensible ego lane boundary. | Retain zero-lane/no-boundary proposal; Human verifies. |
| `dashcam_vietnam_rainnight-0010` | 9.367 | Vehicles, glare and wet-road reflections obscure both ego boundaries; proposal lines are not raw evidence. | Do not accept the proposed 2-lane geometry without Human redraw/review. |
| `dashcam_vietnam_rainnight-0056` | 52.533 | Some pavement contrast is visible but neither boundary nor 3 same-direction lanes is defensible from the frame alone. | Human must inspect the ±1 s video window before choosing a count/polyline. |
| `dashcam_vietnam_rainnight-0059` | 55.350 | A possible right-side marking is interrupted by a motorcycle/reflection; the ego geometry is ambiguous. | Human must inspect the ±1 s video window; retain uncertainty if no boundary is defensible. |

This spot check is AI-assisted QA only. It must not be entered as a Human or
independent second review.

## Reviewer-ready batch plan

Use the built-in review app with the raw-video alias above, and save the actual
reviewer's stable ID. Work in batches of 50–100 frames, run the queue validator
after every batch, and retain `needs_recheck` whenever lane count or boundary
geometry is not defensible.

To reach the 3,000-frame data gate from the present 599-record queue, target
3,000 reviewed records in this balanced allocation:

| Condition slice | Target records | Additional records required from current queue allocation |
|---|---:|---:|
| Rain-night | 500 | 380 |
| Night | 500 | 380 |
| Dense traffic | 1,000 | 820 |
| Day | 1,000 | 821 |
| **Total** | **3,000** | **2,401** |

Within those slices, deliberately select at least 1,000 frames with more than
one defensible same-direction lane and at least 400 frames with faded, missing,
or occluded markings. The latter may overlap rain-night and night but must not
replace clear-polyline supervision.

For the independent-review requirement, allocate 300 already-Human-reviewed
frames proportionally: 50 rain-night, 50 night, 120 dense-traffic and 80 day.
The second reviewer must start from the raw frame/video without seeing the first
reviewer's label. Record disagreements before adjudication; only the final
agreement enters the verified training set.

## Gate status

Fine-tuning remains blocked until the queue has at least 3,000 Human-verified
frames, meets all condition quotas, has 300 independent second reviews with
disagreement at or below 5%, contains zero invalid coordinates, and has no split
leakage. YOLOP remains the active lane baseline.

## Verification

- `repair_lane_review_queue_v2.py --dry-run` passed: 599 records, 0 verified,
  577 pending, 22 needs-recheck, no coordinate or split issue.
- The focused RW-10 suite passed from the `roadwatch/` working directory:
  `11 passed` across repair, queue, gate and secondary-review contracts.
- `verify_lane_quality_gate.py` was rerun after a backup of its prior output.
  It reports `in_progress_pending_verification` and `training_blocked=true`;
  coordinate and split-leakage criteria pass, all Human-review quotas remain at
  zero.

The existing `auto_double_review.py` is only a structural sanity check: its
secondary pass copies the primary label values. It must **not** be cited as an
independent second review or used to claim a disagreement rate. Use two blinded
human passes over raw frames/video, then record their agreement before producing
the double-review report.

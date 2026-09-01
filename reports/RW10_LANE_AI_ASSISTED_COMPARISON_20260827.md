# RW-10 AI-assisted raw-video comparison — 2026-08-27

## Scope and status

This is a 22-frame reference review for manual comparison. It was conducted on
raw frames from `media/dashcam_vietnam_rain+night.mp4`, using the queue alias
`dashcam_vietnam_rainnight.mp4` only to locate timestamps. The reviewer is
recorded as `Codex_AI_Assisted_Reviewer`; this is not a Human review, not a
blinded review, and is ineligible for both `verified` status and the
double-review quota.

The structured record is
`evaluation/rw10_lane_ai_assisted_comparison_20260827.json`.

## Outcome

All 22 frames remain `needs_recheck`. My recommended labels are all
`ground_truth_lane_count = 0`, empty ego-boundary polylines, `uncertain = true`
and `marking_type = ["unknown"]`. In the two short sequences, wet-road glare,
an intersection/crosswalk, headlights and vehicle occlusion prevent a defensible
lane count or ego-lane trace.

Five records disagree with the previous Gemini lane count and should be
adjudicated first:

| Record | Gemini lane count | AI-assisted recommendation | Reason |
|---|---:|---:|---|
| `rainnight-0010` | 2 | 0 | Proposed solid boundaries are reflections/occlusions in the raw sequence. |
| `rainnight-0056` | 3 | 0 | Isolated reflective fragments do not establish three same-direction lanes. |
| `rainnight-0057` | 2 | 0 | A short paint-like fragment is not enough to locate either ego boundary. |
| `rainnight-0059` | 1 | 0 | Motorbike, glare and interrupted fragments make the geometry indeterminate. |
| `rainnight-0060` | 3 | 0 | Adjacent raw frames do not support the proposed three-lane geometry. |

The remaining 17 records agree on lane count zero, although the exact
`not_visible` versus `occluded` category should be confirmed by the named Human
reviewer.

## Manual adjudication

For each record, open the original video at its timestamp and inspect roughly
one second before and after. Do not use proposal-overlay images as evidence. If
the Human reviewer cannot defend a full ego lane boundary, retain the sidecar's
zero-count/no-geometry result with `uncertain = true`; only set `verified` with
the actual reviewer ID after that check.

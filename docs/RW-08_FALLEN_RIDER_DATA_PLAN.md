# RW-08 Fallen Rider Dataset Plan

## Decision

Use a hybrid dataset: real forward-facing dashcam data is the target domain; CARLA is a
synthetic supplement only. Training remains blocked until `dataset_gate()` passes with
auditable evidence.

## Taxonomy

- Image classes: `fallen_person`, `fallen_two_wheeler`.
- Temporal event: `fallen_rider`.
- Temporal confirmation: normal rider → unstable/fall transition → persistent fallen state.
- Required hard negatives include sitting, bending, vehicle repair, parked two-wheelers,
  off-road lying persons, occlusion and road debris.

## Data quality gates

| Gate | Requirement |
|---|---|
| Class coverage | At least 250 instances per image class |
| Negative coverage | `negative_images / positive_images >= 2.0` |
| Adverse coverage | At least 20% of clips are night, rain, low-light or degraded |
| Real validation | At least 30% of positive validation images are real |
| Test domain | 100% real forward-facing dashcam; zero synthetic test samples |
| Split integrity | No source-video/scenario/town/seed/session/camera group crosses splits |
| Provenance | Every source records license, provenance URL and permission type |
| Test independence | Test is locked before training and never used for tuning or checkpoint selection |

## CARLA boundary

The packaged CARLA release does not guarantee an articulated motorcycle rider, a realistic
fall animation, or reliable person–motorcycle separation. Use stock CARLA for staged scenes,
hard negatives and environmental variation. Custom rider poses/animations may require custom
assets and Unreal Engine. Synthetic data never replaces real held-out evaluation.

## Licensing and privacy

Public availability is not training or redistribution permission. Do not ingest ordinary
YouTube/social-media videos under a generic “fair use” claim. Eligible sources are owner
captures with an explicit release, content with compatible documented licenses, or content
with written permission. Record provenance and blur faces/license plates when required.

## Split policy

Group before frame extraction using source video, scenario family, CARLA town, scenario seed,
capture session and camera configuration. Train may mix synthetic and real data. Validation
must contain meaningful real coverage. Test must be real-only and frozen.

## Execution sequence

1. Audit licenses and create source provenance records.
2. Lock real-only test clips without inspecting model performance.
3. Collect/annotate real train and validation clips.
4. Generate CARLA staged positives and hard negatives as supplemental training data.
5. Deduplicate, group-split, calculate manifest statistics and run `dataset_gate()`.
6. Train only after `training_allowed=true`.
7. Promote only with real held-out Recall ≥0.90, Precision ≥0.75 and FAR ≤0.5/min.

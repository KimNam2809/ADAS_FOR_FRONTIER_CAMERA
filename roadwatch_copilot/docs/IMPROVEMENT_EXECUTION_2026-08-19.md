# RoadWatch improvement execution — 2026-08-19

This document records what was implemented, what improved, the evidence used,
and the gates that intentionally remain closed. RoadWatch remains a warning-only
research prototype: it has no steering, braking or throttle actuator API.

## 1. Timestamp Ground Truth and reproducible scoring

Implemented:

- `evaluation/event_ground_truth.json` with verified and provisional event
  windows, negative windows, semantic values and warning deadlines.
- `backend/roadwatch/ground_truth.py` to calculate event TP/FP/FN, precision,
  recall, miss rate, false alerts/min, duplicate rate and time-to-warning.
- `scripts/validate_ground_truth.py`, contact-sheet tooling and unit tests.
- `scripts/evaluate.py` and `scripts/compare_object_models.py` now use real
  timestamp scoring where verified coverage exists.

Evidence: the ground-truth schema validates with zero errors. Current calibrated
A/B contains 52 seconds of verified coverage. It is enough to block unsafe model
promotion, but not enough to claim a production false-alert rate for every video.

## 2. Object detector v1.1 calibration

Implemented:

- Class-aware thresholds for the seven-class candidate.
- Semantic-family tracking for `rider/bicycle/motorcycle`, preventing a track ID
  and message identity from changing when the detector flickers between these
  closely related classes.
- Confidence-weighted stable label voting and family-based alert cooldown keys.
- Promotion gate now includes timestamp recall and timestamp false-alert rate.

Evidence:

| Metric | COCO baseline | Calibrated v1.1 |
|---|---:|---:|
| Timestamp event precision | 0.3077 | 0.3750 |
| Timestamp event recall | 0.5000 | 0.3750 |
| False alerts/min | 10.3846 | 5.7692 |
| Median first warning from clip start | 6.494 s | 4.750 s |
| Object P95 mean | 31.40 ms | 24.04 ms |

Decision: keep `baseline_coco` as default. Calibration made v1.1 cleaner, earlier
and faster in this run, but it missed more verified events. A safety-oriented
promotion gate cannot trade event recall for fewer alerts.

## 3. Traffic Sign Phase 2 and speed-value correction

Implemented:

- 82-class sign training/audit package at `kaggle/train_sign_phase2`.
- 67 locked negative-evaluation frames from the verified no-speed-sign window;
  these remain local/heavy data and are never admitted to training because they
  originate from regression media.
- Mandatory Human Quality Gate before detector fine-tuning.
- A second-stage 10–120 km/h crop classifier training path.
- Runtime `TrafficSignEnsemble`: detector finds the sign, then the optional crop
  classifier resolves the digits. If the classifier is absent or uncertain, the
  existing detector remains the fallback.
- Detector label, classifier result and confidence stay in evidence for audit.

Current evidence: the existing detector still outputs 40 for the physical 60
sign in `test_video10` at about 3.87 s. HUD and TTS now agree with each other, but
both consistently report the same wrong model semantic. The two-stage runtime is
ready; the correction cannot be claimed until `roadwatch_speed_digits_v2.pt` is
trained and passes the locked 40/60/80 regressions.

Blocker: the installed Kaggle CLI no longer accepts the old `KAGGLE_KEY` flow and
reports that OAuth or `KAGGLE_API_TOKEN` is required. No local training was run.

## 4. Regression and application stability

Evidence completed:

- 43 backend tests pass.
- Ground Truth and model registry JSON validate.
- React/TypeScript/Vite production build passes when built to an isolated output
  directory. The normal `dist` directory is owned by the currently logged-in
  desktop process, so the sandbox correctly avoided overwriting it.
- Ten-second DirectML smoke test completes without pipeline error:
  - processed FPS: 7.01 in paced replay;
  - object P95: 24.86 ms;
  - sign P95: 31.85 ms;
  - YOLOP lane P95: 61.08 ms;
  - end-to-end P95: 138.13 ms;
  - overload drop ratio: 0.
- Benchmark storage now uses an isolated evidence database and returns failure
  when `pipeline_error` is present. This fixed a false-success condition found
  during the smoke test.

## 5. UFLDv2 lane candidate

Implemented:

- Official CULane ResNet-18 checkpoint downloaded and exported on CPU to named
  ONNX outputs. Export is conversion only, not local training.
- UFLDv2 pre-processing and row/column-anchor decoder.
- Separate ego-boundary instances instead of turning every visible road marking
  into one lane.
- Candidate profile `ufldv2_fusion`: UFLDv2 supplies lane geometry while YOLOP
  supplies drivable area at a lower refresh rate.
- Conservative night degradation: if UFLDv2 rejects lane geometry, LDW geometry
  is suppressed while drivable-area context remains. YOLOP fragments are not
  accepted as lane boundaries merely because they contain many pixels.

Evidence on 21 fixed frames:

| Metric | YOLOP | UFLDv2 |
|---|---:|---:|
| Usable-quality coverage | 0.3333 | 0.8571 |
| Mean quality | 0.4140 | 0.6878 |
| CPU P50 | 184.77 ms | 124.48 ms |
| CPU P95 | 214.71 ms | 135.07 ms |

Visual review confirms continuous ego boundaries in the daytime 60 km/h scene.
In the difficult night frame, UFLDv2 correctly returned no lane while YOLOP drew
bright fragments across the road; the fusion logic now chooses safe suppression.

Decision: candidate only. `yolop` remains default until all rendered frames and
the full pipeline edge budget pass.

The first full DirectML fusion smoke test completed without provider or pipeline
errors and reached lane P95 124.68 ms plus end-to-end P95 149.37 ms. However,
processed throughput was only 3.04 FPS on the current AMD laptop, below the
12-FPS release gate. The profile therefore remains a research candidate and is
not enabled by default.

## 6. Fallen-rider specialist

Implemented:

- Source/license policy at `configs/fallen_rider_sources.json`.
- Kaggle package at `kaggle/train_fallen_rider` with GPU preflight, class audit,
  sample overlays, SHA-256 split-leakage checks, negative-image gate, license
  gate and target-dashcam-domain gate.
- Exact target taxonomy: `fallen_person`, `fallen_rider`.

The public synthetic fall dataset is accepted only for pretraining because its
camera is overhead CCTV and it is dominated by fallen examples. The public
accident/no-accident dataset is quarantined because scene labels do not localize
a rider and its published license is unknown.

Blocker: no approved forward-dashcam target dataset currently meets the minimum
250 instances per class, 2:1 negative-image ratio, adverse-condition coverage and
video-grouped split rules. Therefore no fallen-rider checkpoint is claimed.

Kaggle Quality Gate Version 1 completed on 2026-08-20 and confirmed the public
candidate must not be promoted: its taxonomy is `laying`/`standing`, it has only
111 unique images, train and validation contain the same 111 SHA-256 image
hashes, there are no negative images, and the viewpoint is fixed indoor CCTV.
The job correctly stopped before training.

## 6.1 Traffic-sign Phase 2 Quality Gate

Kaggle Version 3 completed on 2026-08-20. Automated evidence:

- all 82 classes have instances;
- all 12 speed values from 10 through 120 km/h have crops;
- no image is missing a label file;
- one malformed row was found at `train/labels/8380.txt:4` (six columns);
- `train/images/8380.jpg` is quarantined from both audit counts and training;
- automated Quality Gate passes after quarantine;
- 24 class-stratified overlays were visually inspected and their boxes/classes
  were consistent with the visible signs.

Subsequent semantic review invalidated this provisional pass. Class ID 57 is
declared as `Speed limit 10km/h`, but its crops contain a mixture of visible 10
and 40 km/h signs. In addition, crop `0477_000130.jpg` is an intersection
warning sign annotated as class 2 (`Speed limit 40km/h`). Training therefore
remains blocked. The Quality Gate now requires semantic-purity contact sheets,
quarantines `train/images/0477.jpg`, and cannot pass until every class-57
annotation is corrected or quarantined.

Version 4 expanded the semantic review to all speed values and found additional
contamination: class 41 (`80km/h`) contains visible 60 signs and class 63
(`90km/h`) contains at least one visible 30 sign. It also exposed a pipeline
bug: `End of 50km/h speed limit` was being included in numeric class 50 because
the extractor used a substring match. The extractor now accepts only names
starting with `Speed limit` and embeds the source class ID in every crop name.
Version 5 verified that removing `End of 50km/h speed limit` fixed the extraction
bug, but the remaining class-39 crops still contain visible 80 signs. The source
annotations for speed 10, 50, 80 and 90 therefore require per-annotation cleanup
or replacement with a clean source before any fine-tuning job is approved.

The implementation now collapses all numeric speed-sign detector heads into one
canonical `speed_limit` class. Numeric value recognition is delegated to the
independent crop classifier, matching the runtime ensemble boundary. This makes
10/40 and 60/80 digit-label contamination irrelevant to detector geometry while
preserving `End of 50km/h speed limit` as a separate semantic class. The runtime
accepts the generic detector label only when the crop classifier resolves a
supported value with sufficient confidence; unresolved generic signs do not
produce a numeric TTS claim.

Two additional Kaggle sources were profiled. The full
`maitam/vietnamese-traffic-signs` archive was downloaded and audited: 3,216
images contain 275 speed-40, 189 speed-50, 459 speed-60 and 210 speed-80 boxes.
Its contact sheets show that 40/50 are mostly clean, while the published 60/80
classes contain visible cross-labels. More importantly, adjacent frames from the
same sign sequence are interleaved between the published train and test lists,
so that split is invalid for evaluation. Phase 2 Version 7 therefore attaches
this source only as an OCR-gated classifier supplement and creates a new split
where contiguous numeric frame groups (gap <= 3) cannot cross train/validation.

The `nguyenquyhcmus/vietnamese-traffic-signs` archive was also fully inspected.
Although its taxonomy file lists 52 rows, the archive contains only 39 class
folders and none of the P.127 numeric-speed folders. It is derived from the same
VNTS detection source, so it is rejected both as a speed-data supplement and as
an independent holdout. The reproducible local extraction/contact-sheet tool is
`scripts/audit_vnts_speed.ps1`; all downloaded data and rendered audit evidence
remain under `.cache` and are excluded from Git.

Version 7 confirmed that EasyOCR cannot be the sole numeric-label arbiter. It
rejected most clear VNTS crops and incorrectly promoted visible 40/50 signs into
the cleaned speed-10 folder. Version 7 is therefore rejected and none of those
pseudo-labels are training-authorized. Version 8 replaces OCR-only relabeling
with a temporary digit-cleanup CNN trained from trusted real seeds plus
procedurally rendered signs. Ambiguous crops require agreement across five image
variants, confidence and probability-margin gates; cross-class corrections and
synthetic-only class 10 use stricter thresholds. The bootstrap checkpoint is
explicitly marked `data_cleanup_only`, must pass clean-seed validation, and is
forbidden from runtime promotion. Final model training remains blocked behind
new semantic contact sheets and human approval.

Version 8 correctly remained blocked. Its temporary CNN reached 96.61% training
accuracy but only 88.78% on clean Vietnamese validation seeds; speed 80 and 90
were 50%, and speed 100 was 60.87%. Conservative TTA therefore accepted no
10/50/80/90 crops instead of manufacturing a false pass. Version 9 adds the
CC0-1.0 GTSRB benchmark as clean train-only support for speed
20/30/50/60/70/80/100/120. GTSRB is excluded from every Vietnamese validation
metric. An inverse-frequency sampler prevents the added European classes from
overwhelming synthetic and Vietnamese speed-10/40/90 seeds.

Version 9 raised clean-seed validation to 91.95% and restored speed-100 to
91.30%, proving that clean real imagery reduced part of the synthetic domain
gap. It still accepted no Vietnamese validation crops for 10/50/80 and only one
for 90, while 80/90 clean-seed accuracy remained 50%. Overall accuracy is not
allowed to hide these class failures, so Version 9 remains blocked. Version 10
replaces the from-scratch cleanup CNN with ImageNet-pretrained MobileNetV3-Small
fine-tuned on class-balanced GTSRB, synthetic and trusted Vietnamese seeds. It
also exports confidence-ranked rejection sheets with exact filenames so any
remaining manual curation can be explicit and reproducible rather than based on
whole-folder trust.

## 7. Camera calibration and TTC

Implemented:

- `scripts/calibrate_camera.py`: OpenCV chessboard calibration, camera matrix,
  distortion, RMS reprojection gate and JSON artifact.
- `backend/roadwatch/kinematics.py`: calibration-gated distance, closing-speed
  and TTC telemetry with explicit `telemetry_only` role.
- Metric TTC evidence is never used to trigger FCW before closed-course
  validation.

Current gate: calibration execution correctly fails with `found 0` because no
camera-specific chessboard images exist. `edge_preflight` reports
`metric_ttc_allowed: false`.

## 8. Jetson/TensorRT

Implemented:

- `scripts/jetson_trt_benchmark.py` builds FP16 TensorRT engines with `trtexec`,
  captures throughput, mean GPU compute, P95 latency, engine size and logs.
- Acceptance targets are encoded for object, sign, lane and end-to-end pipeline.
- Existing Jetson Docker profile remains warning-only/read-only.

Blocker: this Windows AMD machine has DirectML and CPU providers, not Jetson
TensorRT. No Jetson benchmark or runtime promotion is claimed. UFLDv2 ONNX is
786.97 MB, so its FP16/INT8 memory and power cost is a mandatory target-hardware
gate rather than an assumption.

## 9. Closed-course validation

`docs/CLOSED_COURSE_VALIDATION.md` defines preconditions, soft-target scenarios,
day/night repetitions, synchronized evidence and release thresholds. No public
road use or actuator integration is authorized.

Current `edge_preflight` truthfully reports:

- `metric_ttc_allowed: false`;
- `jetson_validated: false`;
- `closed_course_validated: false`.

## Required external inputs to continue

1. Correct and re-audit the mixed speed-10/speed-40 annotations; do not approve
   Sign Phase 2 Version 3. Kaggle authentication is working through the local
   `KAGGLE_KEY` compatibility mapping and is never logged.
2. Keep the hard-negative frames extracted from locked regression videos as
   evaluation-only; they are not attached as training input.
3. Obtain and annotate a forward-dashcam fallen-rider dataset meeting the stated
   data gates.
4. Capture at least 12 sharp chessboard images using the exact final camera,
   resolution, crop and mount.
5. Provide Jetson Orin access for TensorRT, memory, thermal and power benchmark.
6. Conduct the documented closed-course protocol with soft targets and measured
   distances before enabling metric TTC for alert evidence.

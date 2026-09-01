# RoadWatch — Real-world remediation and model fine-tuning plan

## 1. Interpretation of test timestamps

Values such as `0.06`, `0.18` and `0.37` in
`REAL_WORLD_TEST_FINDINGS_AND_SPEC.md` are interpreted as the tester's `mm.ss`
notation (`00:06`, `00:18`, `00:37`), not decimal seconds. The four source
videos last 41.84–256.10 seconds, so treating `0.18` as 0.18 seconds would test
the wrong frame. Future regression records must store numeric seconds (`18.0`)
and a display value (`00:18`) separately.

## 2. What was changed now

| Defect | Root cause confirmed in code | Implemented remediation | Verification |
|---|---|---|---|
| Silent FCW after hard braking | FCW required relative closing rate even when the ego and lead vehicle had almost stopped | Added a two-frame-capable, persistent image-space emergency path based on ego-corridor overlap, bbox area/width, bottom proximity, confidence and track age. It emits critical `Cảnh báo va chạm phía trước!`; it never reports metres. | Unit test covers zero closing rate with a very large close lead vehicle. |
| Wrong left/right origin | Origin side was inferred from movement direction | Origin is now derived from the track's first stable horizontal position. | Right-side merge test requires `origin_side=right` and right-side wording. |
| Parked vehicle reported as cross-traffic | Instantaneous lateral velocity was sufficient | Cross-traffic now requires at least five motion observations, minimum rolling displacement and lateral-dominant trajectory. | Static object with detector jitter produces no cross-traffic event. |
| Cut-in reported as cross-traffic | No longitudinal-versus-lateral maneuver gate | A centerward vehicle with longitudinal displacement or bbox approach evidence is classified as cut-in and excluded from cross-traffic. | Right-lane merge produces cut-in only. |
| Car/truck label flicker | Vehicle classes could form separate tracks; class vote accumulated forever | Car/bus/truck now share a tracking family; displayed class uses a confidence-weighted rolling five-observation vote. | A single truck flicker does not replace a stable car label or ID. |
| Wrong speed chosen among lane-specific signs | No reliable lane-to-sign association exists | Conflicting simultaneous speed signs without `lane_binding_confidence >= 0.75` produce an ambiguity advisory instead of asserting 60/80. A bound sign can win later when lane-instance geometry supplies evidence. | Arbitration tests cover ambiguous and lane-bound cases. |

All new motion thresholds are normalized image-space values. The metric rules
in the test specification (`1.0 m`, `1.5 m/s`, heading in degrees) are not
technically valid until camera intrinsics/extrinsics and ego telemetry are
available.

## 3. Findings that are model-limited

### Road-agent detector

- Fallen rider is not in the active seven-class detector taxonomy. A generic
  person/motorcycle detector cannot reliably infer `fallen_person` and
  `fallen_two_wheeler`; the RW-08 specialist dataset gate remains mandatory.
- Far, occluded, rainy and night road users and car-versus-truck confusion are
  detector-domain problems. Temporal voting reduces flicker but cannot recover
  a missed object.
- `roadwatch_objects_v1_1` is not promoted: its offline detector metrics
  improved, but timestamp event recall fell from 0.50 to 0.375. The COCO
  baseline therefore remains active until `RW-OBJECT-V2` passes.

### Lane model

- YOLOP returns a semantic lane mask, not dependable lane instances. It cannot
  consistently count 2/3 lanes, identify a solid divider, or bind an overhead
  speed sign to the ego lane.
- UFLDv2 currently provides better geometric coverage but the fusion pipeline
  measured only 3.04 FPS on the AMD environment and has not passed the verified
  lane ground-truth gate. It remains a candidate.
- Oncoming-road suppression cannot be made safety-reliable from a failed lane
  mask alone. It needs lane direction labels plus temporal flow/heading evidence.

### Traffic-sign orientation

- Rear-facing sign rejection is a detector/classifier data problem. Shape and
  grey-texture heuristics alone would also reject dirty, faded or backlit valid
  signs. Add `sign_front`/`sign_back` hard negatives or an orientation verifier;
  until then the current temporal and visual checks reduce but do not eliminate
  this false positive.

## 4. Object detector fine-tune — `RW-OBJECT-V2`

Executable specification: `configs/finetune_object_v2.json`.

1. Extract candidate frames from all listed target videos at 1 FPS, plus 5 FPS
   inside ±3 seconds of each reported failure. Deduplicate with perceptual hash.
2. Annotate the fixed seven-class taxonomy. Include truncated objects; mark
   ignore regions rather than inventing labels. Add empty-label files for true
   negatives.
3. Split by source video and contiguous scene before frame extraction. No nearby
   frames from one event may cross train/validation/test.
4. Run the annotation gate: at least 2,500 target images, 1,000 negatives and
   the class/condition counts in the JSON plan; visually inspect 200 random and
   class-stratified samples.
5. Train YOLO11n at 640 and 768 pixels. Train YOLO11s only as a teacher/reference;
   it is not automatically suitable for edge deployment.
6. Evaluate detector metrics and then replay the locked RoadWatch event suite.
   Promote only if every gate passes, especially event recall not below baseline,
   false alerts no more than 3/min and P95 latency no more than 1.25× baseline.

AI can automate extraction, deduplication, split validation, Kaggle packaging,
training and scoring. Human review is mandatory for object boxes, ignore regions
and the 100 FP/FN promotion sample.

## 5. Lane fine-tune — `RW-LANE-V2`

Executable specification: `configs/finetune_lane_v2.json`.

1. Sample 3,000+ frames by condition and lane geometry; oversample night, rain,
   faded markings, curves, intersections and multi-lane roads.
2. Annotate ordered lane polylines, ego left/right boundaries, marking type and
   road direction. A semantic foreground mask alone is insufficient.
3. Double-review 300 frames; reviewer disagreement must be at most 5%. Freeze a
   video-grouped real test split before training.
4. Fine-tune UFLDv2 ResNet-18 from CULane weights at 1600×320, then test
   1280×320 and 800×320 edge variants. Keep YOLOP only for drivable-area fusion.
5. Add temporal curve smoothing and confidence rejection; never emit LDW when
   both ego boundaries are not valid.
6. Promote only at lane-count accuracy ≥0.95, ego-boundary F1 ≥0.90,
   night/rain recall ≥0.85, LDW FAR ≤1/min and AMD full-pipeline ≥12 FPS with
   P95 ≤150 ms. The 30 FPS INT8 target is a Jetson hardware gate and cannot be
   certified on EC2 g5g or the AMD laptop.

AI can prepare frames, conversion, training and metrics. Human input is required
for polyline truth and real Jetson validation.

## 6. Ordered next execution

1. Re-run the locked videos with the new P0/P1 rules and record exact numeric
   timestamps, event type, origin side and false alerts/minute.
2. Build and review `RW-OBJECT-V2` target-domain annotation queue.
3. Build and review `RW-LANE-V2` polyline queue in parallel.
4. Submit object fine-tune first because FCW/VRU/cut-in depend on stable tracks.
5. Submit lane fine-tune, benchmark resolution variants, then implement actual
   lane-to-sign binding and oncoming-lane suppression.
6. Train fallen-rider specialist only after the existing RW-08 data gate passes.

The current code changes reduce rule-level failure modes, but they do not claim
that the six real-world cases are closed until video replay metrics and human
review confirm them.

## 7. First real-model replay evidence

The initial replay of `test_video1.mp4` exposed two residual problems: a close
right-side vehicle had `path_conflict=false` under a failed lane mask, and a
track already escalated to critical FCW could later be renamed cross-traffic.
The fail-safe now accepts `near_field_imminent` evidence when lane geometry is
unreliable, and cross-traffic is suppressed after critical FCW for that track.

Final locked replay covered both 00:08–00:24 and 00:26–00:38 sequences. Result:

- scenarios completed: 2/2;
- true positive: 6;
- false positive: 0;
- false negative: 0;
- event precision: 1.0;
- event recall: 1.0;
- unexpected event type: none;
- manifest integrity and automated tests: pass.

Evidence is stored in `reports/real-world-remediation-tv1-verified.json` and its
Markdown rendering. These figures close the two locked `test_video1` windows;
they do not imply the same accuracy on every unseen road or weather condition.

## 8. Full locked-suite result and remaining gap

After the final rule and sign-tracking changes, all six locked scenarios
completed and the integrity/automated-test gates passed. Aggregate event metrics
are `TP=8`, `FP=5`, `FN=2`, precision `0.6154`, recall `0.80`, miss rate `0.20`.
Therefore the harness status is pass, but the model stack is **not production
ready** under the stricter precision/recall interpretation.

- Both false negatives are the night motorcycle crossing and fallen-rider event.
  The active detector labels the rider as `person`; no active model has
  `fallen_person`/`fallen_two_wheeler`. This is a detector/fallen-rider model gap.
- Two corresponding night predictions have the wrong object/maneuver semantics
  (`person` VRU/cut-in), so they are correctly counted as false positives rather
  than being relabeled as successful detections.
- The 60 km/h detector itself was correct on five consecutive frames
  (`confidence 0.91–0.95`), but the previous IoU-only association reset temporal
  hits. Center/scale-aware association now emits speed 60 at 00:04.00.
- Remaining traffic-sign false positives in the 80 km/h clip include a rear-side
  parking restriction and transient conflicting speed classes. These confirm
  the orientation/hard-negative model requirement; they should not be hidden by
  looser scoring.

Full evidence: `reports/real-world-remediation-locked-suite-verified.json`.
The automated suite contains 122 passing tests. Edge preflight also passes all
17 release checks; metric TTC, real Jetson and closed-course gates remain blocked.

## 9. Additional traffic-sign data action

Before the next sign fine-tune, mine every confirmed false sign from `test_video5`
and `test_video11` plus at least 1,000 rear-facing/occluded/gantry hard negatives.
Add an orientation target (`front`, `back`, `ambiguous`) or a small binary
verifier after detection. Promotion requires rear-facing false TTS `0` in the
locked clips, speed-value recall at least `0.95`, and no more than `0.5` false
sign alerts/minute. Lane-specific 60/80 activation remains blocked until
`RW-LANE-V2` supplies verified lane instances and `lane_binding_confidence`.

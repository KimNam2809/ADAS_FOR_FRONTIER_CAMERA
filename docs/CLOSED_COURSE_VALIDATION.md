# RoadWatch closed-course validation protocol

RoadWatch is warning-only. No test may connect its output to steering, braking or
throttle. A safety driver remains responsible for the vehicle, and public-road
testing is prohibited until the closed-course gate is signed off.

## Preconditions

- Written site permission, safety driver, test conductor and independent observer.
- Forward camera rigidly mounted; current `camera_calibration.json` matches the
  exact camera, resolution, crop and mount.
- Braking distance markers measured at 5, 10, 15, 20, 30 and 40 metres.
- Soft targets/mannequins only; no person stands in a collision path.
- Audio level checked inside the cabin; offline mode and read-only vehicle I/O
  verified by `scripts/edge_preflight.py`.
- Test build, model checksums, configuration and vehicle profile frozen.

## Scenarios and minimum repetitions

| ID | Scenario | Day | Night/adverse | Repetitions |
|---|---|---:|---:|---:|
| FCW-01 | Stationary car target in ego lane | yes | yes | 10 each |
| FCW-02 | Lead target decelerates | yes | yes | 10 each |
| CUT-01 | Car cuts in left/right | yes | yes | 10 per side |
| VRU-01 | Pedestrian dummy crosses left/right | yes | yes | 10 per side |
| VRU-02 | Bicycle/motorcycle dummy crosses | yes | yes | 10 per side |
| LANE-01 | Drift toward left/right lane boundary | yes | yes | 10 per side |
| SIGN-01 | 40/50/60/80 speed signs plus hard negatives | yes | yes | 20 per value |
| NEG-01 | Dense traffic with no immediate hazard | yes | yes | 30 minutes |

## Evidence captured for every run

Record synchronized source video, rendered HUD video, JSON event log, audio log,
camera calibration hash, model hashes, source timestamps, ego speed from a
read-only independent logger, measured target distance and observer outcome.

## Release gates

- Critical FCW/VRU event recall >= 0.95 with 95% confidence interval reported.
- Direction/class semantic accuracy >= 0.95.
- Critical time-to-warning: no later than the scenario-specific safe deadline;
  median and P95 are both reported.
- False critical alerts <= 0.1/min and all-alert false rate <= 1/min in NEG-01.
- Duplicate spoken alerts <= 5% of true events.
- Speed-value accuracy >= 0.98 for 40/50/60/80 and zero accepted signs in the
  locked hard-negative window.
- End-to-end P95 latency <= 150 ms on the target edge device at >= 12 processed FPS.
- Metric TTC remains telemetry-only until distance median error <= 10%, P95 error
  <= 20%, and TTC median absolute error <= 0.5 s across all measured distances.

Any failed gate blocks production promotion. The result may still be demonstrated
as an explicitly labelled research prototype using prerecorded video.

# Traffic-sign alerting in RoadWatch

## Why a correct box previously produced no speech

The old pipeline drew every raw detector box, but the Risk Engine converted only
labels matching `Speed limit <n>km/h` into an alert candidate. All other sign
classes stopped before the Governor and therefore could never create a hazard
banner or TTS request.

A speed-limit candidate also had to pass circular geometry, red-ring colour,
IoU-based association, four hits, 0.55 seconds of persistence and a large mandatory
screen-motion score. The hard motion gate rejected genuine signs that moved little.
If another warning occupied the audio slot, the sign was put on a 20-second cooldown
even though it had never been spoken. A source clock starting at zero could also
make a first informational event look as though it was already inside cooldown.

## Implemented flow

```text
raw detector box
  -> explicit 82-class HMI policy
  -> geometry + class-aware visual validation
  -> temporal confirmation
  -> canonical Vietnamese message
  -> Alert Governor priority/cooldown
  -> same payload for hazard banner and TTS
```

The live status now includes `sign_trace`. Each observation records its label,
confidence, box, geometry result, red-ring score, hit count, confirmation time,
motion score and final gate decision. Relevant code:

- `backend/roadwatch/signs.py`: detector-label to HMI policy and canonical message;
- `backend/roadwatch/risk.py`: validation, temporal confirmation and evidence;
- `backend/roadwatch/alerts.py`: priority, cooldown and deferred sign-audio retry;
- `scripts/trace_traffic_signs.py`: standalone video regression trace.

## Driver-notification policy

RoadWatch does not speak every recognized sign. This is deliberate alert-fatigue
control.

### Warning + hazard + TTS

- STOP, no entry and red light;
- pedestrian/children crossing zones;
- road works, accident area, obstacle, danger and slippery road;
- railway crossing, narrow bridge and low-clearance/height restriction.

### Advisory hazard + TTS

- numeric speed limit and end of speed restriction;
- mandatory direction, keep-left, roundabout and lane allocation;
- no turn/U-turn/overtaking and vehicle restrictions;
- sharp bends, narrow road, intersections and populated-area transitions.

### HUD only

- parking and stopping restrictions;
- parking, bus stop, hospital, surveillance camera and U-turn area;
- green light.

FCW/critical road-user hazards always retain priority. A confirmed sign that loses
the audio slot is retried after one second instead of being silently suppressed for
the full sign cooldown.

This policy is aligned with current production and assessment examples:

- Toyota Road Sign Assist describes detection/display of speed limit, STOP,
  do-not-enter and yield signs: https://prd.jsds.tms.aws.toyota.com/home/tools/toyota-safety-sense/
- EU ISA requires a speed-limit information function plus warning/control function,
  visual presentation of the perceived limit, and permits more critical warnings
  such as FCW to suspend speed warning: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32021R1958
- Euro NCAP Vehicle Assistance v1.1 evaluates speed-limit accuracy, advanced limits
  and local hazards and requires speed information in the driver's direct field of
  view: https://www.euroncap.com/media/91705/euro-ncap-protocol-safe-driving-vehicle-assistance-v11.pdf

RoadWatch remains warning-only. It never brakes, steers or changes vehicle speed.

## Measured regression results

Unit/integration tests: `34 passed`.

Direct sign-only ONNX/DirectML traces at production-like 12 FPS:

| Clip/window | Result |
|---|---|
| `test_video11`, 30-36 s | 80 km/h confirmed at 32.67 s; first audio slot was pre-empted, retry was queued at 33.67 s; HUD and spoken messages were identical. |
| `test_video10`, 0-8 s | Detector consistently returned class `Speed limit 40km/h`; hazard and TTS correctly used 40. Visual review proves the physical sign says 60. This is a model semantic error, not a Governor/TTS error. |

Full 12-FPS scans over 180 seconds per video produced:

| Clip | Accepted sign events/min | TTS requests | HUD-only events |
|---|---:|---:|---:|
| `test_video10` | 4.67 | 5 | 9 |
| `test_video11` | 3.67 | 5 | 6 |

Thus the expanded taxonomy did not speak on every raw box: only 10 TTS requests
were created across roughly six minutes, while low-value signs remained visual.

Evidence:

- `reports/traffic-sign-trace-test11-12fps.json`
- `reports/traffic-sign-trace-test10-12fps.json`
- `reports/traffic-sign-full-12fps.json`
- `reports/test_video10-sign-4.13s.jpg`

The real Piper Vietnamese voice was also smoke-tested with the 80 km/h canonical
sentence. It generated and played a 137,802-byte local WAV with no provider error.

## Remaining model-quality gate

The 82-class model cannot be considered production-ready for numeric speed limits:
at 4.13 seconds in `test_video10`, it assigns high confidence to 40 although the
sign visibly reads 60. TTS must never invent a correction that the perception model
did not establish.

The next sign model must use:

1. timestamped crops from `test_video10`/`test_video11` as a locked test set;
2. hard negatives from the no-sign daytime window in `video_test`;
3. balanced examples for each numeric speed value;
4. a two-stage design if using the 121-class Roboflow dataset, because its class
   `129_TocDoToiDa` identifies the sign category but does not encode the number;
5. a separate lightweight digit classifier/OCR head for 10-120 km/h;
6. promotion gates for speed-value accuracy, false speed alerts/minute, temporal
   stability, latency and HUD/TTS equality.

The referenced Roboflow dataset currently reports 4,237 images, 121 classes,
CC BY 4.0, and zero published dataset versions. It can support Vietnamese sign
category coverage after audit, but cannot be downloaded through the normal version
API until a version is created/forked:
https://universe.roboflow.com/haitran/vietnam-traffic-signs-ihczr

## Reproduce

```powershell
.\.venv\Scripts\python.exe .\scripts\trace_traffic_signs.py `
  test_video10.mp4 --sample-fps 12 --start 0 --duration 8 `
  --output reports/traffic-sign-trace-test10-12fps.json

.\.venv\Scripts\python.exe .\scripts\trace_traffic_signs.py `
  test_video11.mp4 --sample-fps 12 --start 30 --duration 6 `
  --output reports/traffic-sign-trace-test11-12fps.json
```

Read `gate_decision_counts`, `events`, and per-frame `observations[].trace` to
distinguish model misses/misclassification from policy, cooldown and audio faults.

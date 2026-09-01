# RoadWatch Regression Report

- Status: **FAIL**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `1515373398D34F1535DCD00BBDD7553A8659C57B0DD312F84ECDE0566475E297`
- Scenarios: 6/6 completed
- Event precision/recall: 0.5000 / 0.6000
- Unexpected event types: none

## Gates

| Gate | Result |
|---|---|
| `manifest_and_hash_integrity` | PASS |
| `all_scenarios_completed` | PASS |
| `no_unexpected_event_type` | PASS |
| `all_scenarios_have_measured_ground_truth` | PASS |
| `automated_tests` | FAIL |

## Scenarios

| ID | Completed | Events | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| `locked-tv1-cutin-braking-1` | yes | 3 | 2 | 1 | 1 |
| `locked-tv1-cutin-braking-2` | yes | 3 | 2 | 1 | 1 |
| `locked-video-test-night` | yes | 1 | 0 | 1 | 2 |
| `locked-video-test-no-speed` | yes | 9 | 0 | 0 | 0 |
| `locked-tv10-speed-60` | yes | 1 | 1 | 0 | 0 |
| `locked-tv11-speed-80` | yes | 4 | 1 | 3 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

# RoadWatch Regression Report

- Status: **PASS**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `81B6E2528A8180C64E5C34602389099C72015DE1C569E2495AD73532DD78E121`
- Scenarios: 7/7 completed
- Event precision/recall: 0.0685 / 0.5556
- Unexpected event types: none

## Gates

| Gate | Result |
|---|---|
| `manifest_and_hash_integrity` | PASS |
| `all_scenarios_completed` | PASS |
| `no_unexpected_event_type` | PASS |
| `all_scenarios_have_measured_ground_truth` | PASS |
| `automated_tests` | PASS |

## Scenarios

| ID | Completed | Events | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| `locked-tv1-cutin-braking-1` | yes | 3 | 1 | 2 | 1 |
| `locked-tv1-cutin-braking-2` | yes | 3 | 1 | 2 | 1 |
| `rw02-dashcam-vn-001` | yes | 12 | 0 | 12 | 1 |
| `rw02-dashcam-vn-014` | yes | 11 | 1 | 10 | 0 |
| `rw02-dashcam-vn-018` | yes | 13 | 1 | 12 | 0 |
| `rw02-dashcam-vn-026` | yes | 16 | 0 | 16 | 1 |
| `rw02-dashcam-vn-048` | yes | 15 | 1 | 14 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

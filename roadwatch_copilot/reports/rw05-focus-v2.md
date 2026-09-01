# RoadWatch Regression Report

- Status: **PASS**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `7BE6C889CC8F8A1D2A3111D653DDC25AE762A5AFC138358423B10265E5EC7893`
- Scenarios: 7/7 completed
- Event precision/recall: 0.0795 / 0.7778
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
| `locked-tv1-cutin-braking-1` | yes | 4 | 1 | 3 | 1 |
| `locked-tv1-cutin-braking-2` | yes | 3 | 1 | 2 | 1 |
| `rw02-dashcam-vn-001` | yes | 15 | 1 | 14 | 0 |
| `rw02-dashcam-vn-014` | yes | 15 | 1 | 14 | 0 |
| `rw02-dashcam-vn-018` | yes | 15 | 1 | 14 | 0 |
| `rw02-dashcam-vn-026` | yes | 18 | 1 | 17 | 0 |
| `rw02-dashcam-vn-048` | yes | 18 | 1 | 17 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

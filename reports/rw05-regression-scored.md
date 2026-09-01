# RoadWatch Regression Report

- Status: **PASS**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `7BE6C889CC8F8A1D2A3111D653DDC25AE762A5AFC138358423B10265E5EC7893`
- Scenarios: 37/37 completed
- Event precision/recall: 0.0427 / 0.8750
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
| `locked-tv1-cutin-braking-1` | yes | 4 | 2 | 2 | 0 |
| `locked-tv1-cutin-braking-2` | yes | 4 | 2 | 2 | 0 |
| `locked-video-test-night` | yes | 3 | 2 | 1 | 0 |
| `locked-video-test-no-speed` | yes | 28 | 0 | 0 | 0 |
| `locked-tv10-speed-60` | yes | 0 | 0 | 0 | 1 |
| `locked-tv11-speed-80` | yes | 2 | 1 | 1 | 0 |
| `rw02-dashcam-vn-001` | yes | 16 | 1 | 15 | 0 |
| `rw02-dashcam-vn-004` | yes | 23 | 1 | 22 | 0 |
| `rw02-dashcam-vn-007` | yes | 12 | 1 | 11 | 0 |
| `rw02-dashcam-vn-014` | yes | 14 | 1 | 13 | 0 |
| `rw02-dashcam-vn-017` | yes | 22 | 1 | 21 | 0 |
| `rw02-dashcam-vn-018` | yes | 14 | 1 | 13 | 0 |
| `rw02-dashcam-vn-021` | yes | 12 | 1 | 11 | 0 |
| `rw02-dashcam-vn-026` | yes | 18 | 1 | 17 | 0 |
| `rw02-dashcam-vn-027` | yes | 20 | 1 | 19 | 0 |
| `rw02-dashcam-vn-029` | yes | 19 | 1 | 18 | 0 |
| `rw02-dashcam-vn-030` | yes | 18 | 1 | 17 | 0 |
| `rw02-dashcam-vn-037` | yes | 18 | 0 | 18 | 1 |
| `rw02-dashcam-vn-039` | yes | 10 | 1 | 9 | 0 |
| `rw02-dashcam-vn-048` | yes | 18 | 1 | 17 | 0 |
| `rw02-dashcam-vn-050` | yes | 18 | 0 | 18 | 1 |
| `rw02-dashcam-vn-051` | yes | 14 | 1 | 13 | 0 |
| `rw02-dashcam-vn-013` | yes | 16 | 0 | 16 | 0 |
| `rw02-dashcam-vn-010` | yes | 18 | 0 | 18 | 0 |
| `rw02-dashcam-vn-009` | yes | 9 | 0 | 9 | 0 |
| `rw02-dashcam-vn-054` | yes | 20 | 0 | 20 | 0 |
| `rw02-dashcam-vn-059` | yes | 6 | 0 | 6 | 0 |
| `rw02-dashcam-vn-035` | yes | 23 | 0 | 23 | 0 |
| `rw02-dashcam-vn-056` | yes | 14 | 0 | 14 | 0 |
| `rw02-dashcam-vn-023` | yes | 14 | 0 | 14 | 0 |
| `rw02-dashcam-vn-024` | yes | 19 | 0 | 19 | 0 |
| `rw02-dashcam-vn-033` | yes | 15 | 0 | 15 | 0 |
| `rw02-dashcam-vn-031` | yes | 14 | 0 | 14 | 0 |
| `rw02-dashcam-vn-052` | yes | 7 | 0 | 7 | 0 |
| `rw02-dashcam-vn-060` | yes | 3 | 0 | 3 | 0 |
| `rw02-dashcam-vn-034` | yes | 21 | 0 | 21 | 0 |
| `rw02-dashcam-vn-055` | yes | 14 | 0 | 14 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

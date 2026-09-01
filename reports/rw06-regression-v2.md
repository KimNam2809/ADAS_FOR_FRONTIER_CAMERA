# RoadWatch Regression Report

- Status: **PASS**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `623050A3307DA7CF5D1A226E4B833DF7718D3FFB4CB674182C104929A6F18AC8`
- Scenarios: 37/37 completed
- Event precision/recall: 0.0307 / 0.4583
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
| `locked-tv1-cutin-braking-2` | yes | 3 | 2 | 1 | 0 |
| `locked-video-test-night` | yes | 3 | 0 | 3 | 2 |
| `locked-video-test-no-speed` | yes | 19 | 0 | 0 | 0 |
| `locked-tv10-speed-60` | yes | 0 | 0 | 0 | 1 |
| `locked-tv11-speed-80` | yes | 2 | 1 | 1 | 0 |
| `rw02-dashcam-vn-001` | yes | 15 | 1 | 14 | 0 |
| `rw02-dashcam-vn-004` | yes | 20 | 0 | 20 | 1 |
| `rw02-dashcam-vn-007` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-014` | yes | 10 | 0 | 10 | 1 |
| `rw02-dashcam-vn-017` | yes | 14 | 0 | 14 | 1 |
| `rw02-dashcam-vn-018` | yes | 9 | 1 | 8 | 0 |
| `rw02-dashcam-vn-021` | yes | 9 | 0 | 9 | 1 |
| `rw02-dashcam-vn-026` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-027` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-029` | yes | 13 | 0 | 13 | 1 |
| `rw02-dashcam-vn-030` | yes | 11 | 1 | 10 | 0 |
| `rw02-dashcam-vn-037` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-039` | yes | 9 | 1 | 8 | 0 |
| `rw02-dashcam-vn-048` | yes | 12 | 1 | 11 | 0 |
| `rw02-dashcam-vn-050` | yes | 12 | 0 | 12 | 1 |
| `rw02-dashcam-vn-051` | yes | 11 | 1 | 10 | 0 |
| `rw02-dashcam-vn-013` | yes | 13 | 0 | 13 | 0 |
| `rw02-dashcam-vn-010` | yes | 14 | 0 | 14 | 0 |
| `rw02-dashcam-vn-009` | yes | 7 | 0 | 7 | 0 |
| `rw02-dashcam-vn-054` | yes | 13 | 0 | 13 | 0 |
| `rw02-dashcam-vn-059` | yes | 5 | 0 | 5 | 0 |
| `rw02-dashcam-vn-035` | yes | 16 | 0 | 16 | 0 |
| `rw02-dashcam-vn-056` | yes | 10 | 0 | 10 | 0 |
| `rw02-dashcam-vn-023` | yes | 10 | 0 | 10 | 0 |
| `rw02-dashcam-vn-024` | yes | 14 | 0 | 14 | 0 |
| `rw02-dashcam-vn-033` | yes | 10 | 0 | 10 | 0 |
| `rw02-dashcam-vn-031` | yes | 11 | 0 | 11 | 0 |
| `rw02-dashcam-vn-052` | yes | 5 | 0 | 5 | 0 |
| `rw02-dashcam-vn-060` | yes | 3 | 0 | 3 | 0 |
| `rw02-dashcam-vn-034` | yes | 17 | 0 | 17 | 0 |
| `rw02-dashcam-vn-055` | yes | 9 | 0 | 9 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

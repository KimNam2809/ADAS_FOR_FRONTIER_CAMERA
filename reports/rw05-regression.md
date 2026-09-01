# RoadWatch Regression Report

- Status: **PASS**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `29A39B0511DB2CBBC5AAA2B10D2DD94B9A7484C1ECA3871A3454F4CD0188FDF9`
- Scenarios: 37/37 completed
- Event precision/recall: 0.0305 / 0.3750
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
| `locked-tv1-cutin-braking-1` | yes | 0 | 0 | 0 | 2 |
| `locked-tv1-cutin-braking-2` | yes | 3 | 1 | 2 | 1 |
| `locked-video-test-night` | yes | 2 | 1 | 1 | 1 |
| `locked-video-test-no-speed` | yes | 14 | 0 | 0 | 0 |
| `locked-tv10-speed-60` | yes | 0 | 0 | 0 | 1 |
| `locked-tv11-speed-80` | yes | 1 | 1 | 0 | 0 |
| `rw02-dashcam-vn-001` | yes | 10 | 0 | 10 | 1 |
| `rw02-dashcam-vn-004` | yes | 18 | 1 | 17 | 0 |
| `rw02-dashcam-vn-007` | yes | 10 | 1 | 9 | 0 |
| `rw02-dashcam-vn-014` | yes | 7 | 0 | 7 | 1 |
| `rw02-dashcam-vn-017` | yes | 13 | 0 | 13 | 1 |
| `rw02-dashcam-vn-018` | yes | 9 | 0 | 9 | 1 |
| `rw02-dashcam-vn-021` | yes | 6 | 1 | 5 | 0 |
| `rw02-dashcam-vn-026` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-027` | yes | 15 | 0 | 15 | 1 |
| `rw02-dashcam-vn-029` | yes | 8 | 1 | 7 | 0 |
| `rw02-dashcam-vn-030` | yes | 10 | 1 | 9 | 0 |
| `rw02-dashcam-vn-037` | yes | 7 | 0 | 7 | 1 |
| `rw02-dashcam-vn-039` | yes | 7 | 0 | 7 | 1 |
| `rw02-dashcam-vn-048` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-050` | yes | 15 | 0 | 15 | 1 |
| `rw02-dashcam-vn-051` | yes | 10 | 1 | 9 | 0 |
| `rw02-dashcam-vn-013` | yes | 10 | 0 | 10 | 0 |
| `rw02-dashcam-vn-010` | yes | 11 | 0 | 11 | 0 |
| `rw02-dashcam-vn-009` | yes | 3 | 0 | 3 | 0 |
| `rw02-dashcam-vn-054` | yes | 12 | 0 | 12 | 0 |
| `rw02-dashcam-vn-059` | yes | 4 | 0 | 4 | 0 |
| `rw02-dashcam-vn-035` | yes | 15 | 0 | 15 | 0 |
| `rw02-dashcam-vn-056` | yes | 8 | 0 | 8 | 0 |
| `rw02-dashcam-vn-023` | yes | 8 | 0 | 8 | 0 |
| `rw02-dashcam-vn-024` | yes | 12 | 0 | 12 | 0 |
| `rw02-dashcam-vn-033` | yes | 8 | 0 | 8 | 0 |
| `rw02-dashcam-vn-031` | yes | 8 | 0 | 8 | 0 |
| `rw02-dashcam-vn-052` | yes | 2 | 0 | 2 | 0 |
| `rw02-dashcam-vn-060` | yes | 2 | 0 | 2 | 0 |
| `rw02-dashcam-vn-034` | yes | 12 | 0 | 12 | 0 |
| `rw02-dashcam-vn-055` | yes | 7 | 0 | 7 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

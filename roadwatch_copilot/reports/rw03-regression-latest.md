# RoadWatch Regression Report

- Status: **FAIL**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `5664813DA86EAFB5C85D5F8EDE5C5257A49AD4E3C80F6DD6D56A670815A165F6`
- Scenarios: 37/37 completed
- Event precision/recall: 0.0335 / 0.7083
- Unexpected event types: none

## Gates

| Gate | Result |
|---|---|
| `manifest_and_hash_integrity` | PASS |
| `all_scenarios_completed` | PASS |
| `no_unexpected_event_type` | PASS |
| `all_scenarios_have_measured_ground_truth` | FAIL |
| `automated_tests` | PASS |

## Scenarios

| ID | Completed | Events | TP | FP | FN |
|---|---:|---:|---:|---:|---:|
| `locked-tv1-cutin-braking-1` | yes | 4 | 2 | 2 | 0 |
| `locked-tv1-cutin-braking-2` | yes | 4 | 2 | 2 | 0 |
| `locked-video-test-night` | yes | 3 | 1 | 2 | 1 |
| `locked-video-test-no-speed` | yes | 32 | 0 | 0 | 0 |
| `locked-tv10-speed-60` | yes | 1 | 0 | 1 | 1 |
| `locked-tv11-speed-80` | yes | 4 | 1 | 3 | 0 |
| `rw02-dashcam-vn-001` | yes | 19 | 1 | 18 | 0 |
| `rw02-dashcam-vn-004` | yes | 23 | 1 | 22 | 0 |
| `rw02-dashcam-vn-007` | yes | 13 | 1 | 12 | 0 |
| `rw02-dashcam-vn-014` | yes | 16 | 1 | 15 | 0 |
| `rw02-dashcam-vn-017` | yes | 19 | 0 | 19 | 1 |
| `rw02-dashcam-vn-018` | yes | 14 | 1 | 13 | 0 |
| `rw02-dashcam-vn-021` | yes | 13 | 1 | 12 | 0 |
| `rw02-dashcam-vn-026` | yes | 17 | 1 | 16 | 0 |
| `rw02-dashcam-vn-027` | yes | 20 | 0 | 20 | 1 |
| `rw02-dashcam-vn-029` | yes | 20 | 1 | 19 | 0 |
| `rw02-dashcam-vn-030` | yes | 19 | 1 | 18 | 0 |
| `rw02-dashcam-vn-037` | yes | 17 | 0 | 17 | 1 |
| `rw02-dashcam-vn-039` | yes | 11 | 0 | 11 | 1 |
| `rw02-dashcam-vn-048` | yes | 19 | 1 | 18 | 0 |
| `rw02-dashcam-vn-050` | yes | 18 | 0 | 18 | 1 |
| `rw02-dashcam-vn-051` | yes | 16 | 1 | 15 | 0 |
| `rw02-dashcam-vn-013` | yes | 15 | 0 | 15 | 0 |
| `rw02-dashcam-vn-010` | yes | 20 | 0 | 20 | 0 |
| `rw02-dashcam-vn-009` | yes | 9 | 0 | 9 | 0 |
| `rw02-dashcam-vn-054` | yes | 16 | 0 | 16 | 0 |
| `rw02-dashcam-vn-059` | yes | 5 | 0 | 5 | 0 |
| `rw02-dashcam-vn-035` | yes | 21 | 0 | 21 | 0 |
| `rw02-dashcam-vn-056` | yes | 11 | 0 | 11 | 0 |
| `rw02-dashcam-vn-023` | yes | 17 | 0 | 17 | 0 |
| `rw02-dashcam-vn-024` | yes | 20 | 0 | 20 | 0 |
| `rw02-dashcam-vn-033` | yes | 14 | 0 | 14 | 0 |
| `rw02-dashcam-vn-031` | yes | 16 | 0 | 16 | 0 |
| `rw02-dashcam-vn-052` | yes | 12 | 0 | 12 | 0 |
| `rw02-dashcam-vn-060` | yes | 4 | 0 | 4 | 0 |
| `rw02-dashcam-vn-034` | yes | 23 | 0 | 23 | 0 |
| `rw02-dashcam-vn-055` | yes | 15 | 0 | 15 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

# RoadWatch Regression Report

- Status: **FAIL**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `5664813DA86EAFB5C85D5F8EDE5C5257A49AD4E3C80F6DD6D56A670815A165F6`
- Scenarios: 1/1 completed
- Event precision/recall: 0.0000 / 0.0000
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
| `locked-tv10-speed-60` | yes | 1 | 0 | 1 | 1 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

# RoadWatch Regression Report

- Status: **FAIL**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `415662C677A29C4855A56DFB2191FD5C7B945878B705BA3F49A5D468E3DE1D72`
- Scenarios: 1/1 completed
- Event precision/recall: 0.6667 / 1.0000
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
| `locked-tv1-cutin-braking-1` | yes | 3 | 2 | 1 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

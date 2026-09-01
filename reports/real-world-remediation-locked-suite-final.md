# RoadWatch Regression Report

- Status: **PASS**
- Release: `roadwatch-r0-2026-08-21`
- Seed: `162`
- Config SHA-256: `EEE13EEC913574A2EF07710335C4FF3151DBD28E8323E4750146DF37078F6E20`
- Scenarios: 6/6 completed
- Event precision/recall: 0.7778 / 0.7000
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
| `locked-tv1-cutin-braking-1` | yes | 3 | 3 | 0 | 0 |
| `locked-tv1-cutin-braking-2` | yes | 3 | 3 | 0 | 0 |
| `locked-video-test-night` | yes | 2 | 0 | 2 | 2 |
| `locked-video-test-no-speed` | yes | 17 | 0 | 0 | 0 |
| `locked-tv10-speed-60` | yes | 0 | 0 | 0 | 1 |
| `locked-tv11-speed-80` | yes | 1 | 1 | 0 | 0 |

> Precision/recall phản ánh baseline hiện tại trên phần coverage đã khóa; RW-03 chỉ chứng minh regression harness có thể tái lập và chặn sai taxonomy/hash, không tự động promote model khi metric thấp.

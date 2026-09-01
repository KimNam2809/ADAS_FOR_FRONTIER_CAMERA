# RW-00 — Release Baseline và Runtime Sync

Ngày thực hiện: 2026-08-21  
Release: `roadwatch-r0-2026-08-21` (`R0`)  
Trạng thái: **PASS**

## Vấn đề đã xử lý

`configs/model_registry.json` và `configs/default.json` đã promote bộ nhận diện biển báo Phase 2, nhưng `configs/runtime.json` cục bộ vẫn ghi đè bằng `yolo11s_vietnam_traffic`. Vì vậy ứng dụng có thể chạy model cũ dù tài liệu và registry tuyên bố model mới đang active.

## Thay đổi

- Thêm `configs/release_manifest.json` làm nguồn xác thực release, profile và SHA-256 của các model active.
- Thêm `backend/roadwatch/release.py` để đối chiếu config, registry, filename và model bytes.
- Thêm `scripts/release_preflight.py`; exit code `0` khi pass, `1` khi có drift.
- Đồng bộ runtime cục bộ sang `roadwatch_detector_v2` và `roadwatch_speed_digits_v2`.
- `/api/health` và `scripts/edge_preflight.py` nay công bố trạng thái release; health bị hạ xuống `degraded` nếu có drift.

## Bằng chứng

- Release preflight: `24/24` checks pass, gồm 7 SHA-256 model.
- Unit/integration tests bổ sung kiểm tra ba trường hợp: release hợp lệ, runtime model cũ và hash sai.
- Lệnh tái lập:

```powershell
roadwatch\.venv\Scripts\python.exe roadwatch\scripts\release_preflight.py
roadwatch\.venv\Scripts\python.exe -m pytest roadwatch\tests -q
```

File `reports/release-preflight-latest.json` là bằng chứng máy đọc được và không được dùng để thay thế manifest đã track.

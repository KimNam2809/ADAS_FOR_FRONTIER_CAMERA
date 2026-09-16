# RoadWatch phone-first Kaggle automation

Control plane này cho phép chủ dự án dùng **điện thoại + ứng dụng GitHub/ChatGPT** để submit, theo dõi và tải bằng chứng huấn luyện Kaggle. GitHub Actions chỉ điều phối; mọi train nặng chạy trên Kaggle GPU, không chạy trên GitHub runner hoặc laptop AMD.

## Thiết lập một lần trên GitHub

Repository `KimNam2809/ADAS_FOR_FRONTIER_CAMERA` cần các **Actions secrets**:

```text
KAGGLE_USERNAME_ACCOUNT_1
KAGGLE_API_TOKEN_ACCOUNT_1
KAGGLE_USERNAME_ACCOUNT_2
KAGGLE_API_TOKEN_ACCOUNT_2
ROBOFLOW_KEY
```

Và **Actions variables**:

```text
ROADWATCH_KAGGLE_OWNER=lekimnam
KAGGLE_DEFAULT_ACCOUNT=account_1
AUTO_PROMOTE=false
MAX_AUTO_RETRIES=1
ARTIFACT_RETENTION_DAYS=14
```

`GEMINI_API_KEY` không cần cho pipeline Kaggle hiện tại và không được upload. `.env` chỉ tồn tại local, bị ignore và tuyệt đối không được đính kèm issue/log.

Kết quả preflight ngày 2026-09-17: `account_1` đọc được đủ bốn input của
traffic-sign pipeline. `account_2` xác thực được và đọc ba dataset public nhưng
Kaggle API vẫn từ chối private seed `lekimnam/roadwatch-vietnam-sign-seed-model`.
Vì vậy traffic-sign pilot/full hiện phải chọn `account_1`; `account_2` dành cho
lane hoặc chỉ dùng traffic-sign sau khi API preflight của private seed PASS.

## Chạy pilot chỉ bằng điện thoại

1. Mở GitHub → repository RoadWatch → **Actions**.
2. Chọn **Kaggle · Traffic Sign Pilot**.
3. Chọn **Run workflow**, account `account_1` hoặc `account_2`.
4. Workflow chạy credential/dataset preflight, tạo package bất biến và submit Kaggle GPU.
5. Mở issue `[Kaggle][Pilot] ...` để lấy link trực tiếp tới job.
6. Khi Kaggle báo xong, chạy **Kaggle · Job Status** với `owner/kernel-slug` trong issue.
7. Nếu `COMPLETE`, chạy **Kaggle · Download Evidence` để lấy output dưới dạng GitHub artifact.
8. Gửi status/log đã redacted trong cuộc trò chuyện với Bao Công. Không gửi token.

## Chạy full

Chỉ sau khi pilot Quality Gate được xác nhận:

1. Actions → **Kaggle · Traffic Sign Full**.
2. Chọn account có quota GPU.
3. Nhập chính xác `RUN_FULL`.
4. Candidate full vẫn có nhãn `promotion-blocked`; job COMPLETE không đồng nghĩa model được promote.

## Xử lý lỗi qua điện thoại

| Hiện tượng | Thao tác |
|---|---|
| `Missing secret` | GitHub → Settings → Secrets and variables → Actions; sửa secret rồi chạy lại workflow |
| `dataset_denied` | Chia sẻ private dataset cho đúng Kaggle account, mở dataset một lần, chạy lại pilot |
| `QUEUED` | Chờ quota/worker Kaggle; không submit bản trùng |
| `ERROR` | Chạy Job Status, tải diagnostics/evidence và gửi phần log đã che secret |
| OOM/NaN/taxonomy sai | Dừng; không tự retry full và không promote |
| Workflow lỗi tạm thời API | Chạy lại tối đa một lần; không tạo nhiều kernel song song |

ChatGPT trên điện thoại có thể đọc ảnh/log hoặc nội dung artifact được gửi trong cuộc trò chuyện và đề xuất patch. Để tự sửa repository, cần dùng cùng task có quyền truy cập repo/host hoặc tạo PR mới; ứng dụng ChatGPT đơn thuần không tự có credential GitHub/Kaggle nếu chưa kết nối.

## Safety gates

- GPU là bắt buộc; preflight fail-closed nếu dataset không truy cập được.
- Pilot mặc định 1 epoch để xác nhận kỹ thuật, không dùng để promote.
- Full cần chuỗi xác nhận rõ ràng.
- Evaluation chỉ tạo `PASS_PENDING_HUMAN_GATE`.
- Promotion workflow chỉ tạo request; không sửa active model và không `git push` model.
- Model/video/dataset/secret không được commit Git.

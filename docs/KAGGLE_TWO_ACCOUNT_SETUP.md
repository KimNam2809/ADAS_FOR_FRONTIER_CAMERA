# RoadWatch — Thiết lập hai Kaggle account hợp lệ

Tài liệu này mô tả cách dùng credential tách biệt cho các kernel RoadWatch.
Nó không được dùng để né quota hoặc vận hành nhiều account do cùng một người
kiểm soát nếu việc đó trái với chính sách Kaggle.

## Cấu hình local

Trong `roadwatch/.env`, dùng tên biến không trùng:

```dotenv
USERNAME_ACCOUNT_1=<Kaggle username account 1>
KAGGLE_API_TOKEN_ACCOUNT_1=<token account 1>
USERNAME_ACCOUNT_2=<Kaggle username account 2>
KAGGLE_API_TOKEN_ACCOUNT_2=<token account 2>
```

Không gửi token qua chat và không commit `.env`.

## Kiểm tra credential

Chạy tại thư mục `roadwatch`:

```powershell
.\scripts\kaggle_account_preflight.ps1 -Account 1
.\scripts\kaggle_account_preflight.ps1 -Account 2
```

Các lệnh này chỉ gọi `quota`, `kernels list`, `datasets list` và `datasets files`
để kiểm tra quyền đọc; không dùng `datasets status` vì lệnh đó có thể yêu cầu
quyền owner/status. Chúng không submit kernel, không tải dataset và không dùng
GPU. Output được lưu tại:

```text
reports/kaggle_account_1_preflight.json
reports/kaggle_account_2_preflight.json
```

## Trạng thái hiện tại

- Account 1: authentication và quota hợp lệ; đang sở hữu Object pilot.
- Account 2: authentication và quota hợp lệ.
- Account 2 trước correction chưa có quyền đọc qua API; sau khi cấp quyền và
  dùng phép kiểm tra `datasets files`, quyền đọc được xác nhận:
  - `lekimnam/roadwatch-target-domain-videos-v1`
  - `lekimnam/roadwatch-lane-teacher-models-v1`
- Vì preflight cũ dùng sai endpoint nên từng báo pending; quyền file-list hiện đã
  được xác nhận, nhưng Lane fine-tune vẫn block bởi thiếu 3.000 verified frames.

## Cấp quyền private dataset

Human owner của dataset cần thực hiện trên Kaggle:

1. Mở trang dataset.
2. Vào `Settings` hoặc `Sharing/Collaborators`.
3. Thêm đúng Kaggle username của Account 2.
4. Chọn quyền đọc/collaborator phù hợp.
5. Lặp lại cho cả hai dataset private.
6. Chờ lời mời được chấp nhận nếu Kaggle yêu cầu.

Không chuyển dataset sang public chỉ để chạy thử nếu chưa có quyết định về dữ
liệu. Private Notebook và private Dataset có quyền riêng; account thứ hai phải
được cấp quyền riêng.

## Quy tắc kernel

- Object V3 pilot hiện tại tiếp tục dùng Account 1.
- Lane kernel tương lai có thể dùng Account 2 sau khi `kaggle_account_2_preflight.ps1`
  trả `status = READY`.
- Mỗi kernel phải khai báo input đúng owner/slug và lưu preflight, status,
  metrics, artifact hash.
- Không promote candidate chỉ vì kernel chạy thành công.

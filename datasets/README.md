# RoadWatch datasets

Thư mục này chỉ lưu local hoặc mount từ ổ dữ liệu; ảnh/video/label nặng không được commit.

## Cấu trúc đề xuất

```text
datasets/
├── raw/                 # Bản tải nguyên gốc, bất biến
├── interim/             # Sau convert/clean
├── roadwatch_vn/        # Nhãn Việt Nam đã kiểm tra
│   ├── images/train|val|test
│   └── labels/train|val|test
└── manifests/           # Data card, checksum, split theo video
```

Quy tắc bắt buộc:

- Split theo video/sequence, không chia ngẫu nhiên các frame gần nhau.
- Lưu nguồn, license, checksum và mapping nhãn trong data card.
- Không trộn `rider`, `motor`, `motorcycle`, `bike`, `bicycle` nếu chưa có mapping được duyệt.
- Test set RoadWatch không được dùng để train hoặc chọn threshold.
- Mọi model mới phải đánh giá cả detection metric và scenario alert metric.

Không có dataset nào được tải tự động bởi project để tránh vi phạm license và làm đầy ổ đĩa.

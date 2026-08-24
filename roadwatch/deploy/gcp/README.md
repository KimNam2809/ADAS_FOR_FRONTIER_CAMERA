# RoadWatch GCP deployment (project `c3-roadwatch-162`)

Đây là scaffold triển khai public demo bằng GCP, không dùng Firebase. Cloud Run
phục vụ React/FastAPI; video/model nặng không nằm trong Git và cũng không được
giả định có sẵn trong container.

## Đã có trong scaffold

- Cloud Build build/push image vào Artifact Registry rồi deploy Cloud Run.
- Region mặc định `asia-southeast1`.
- Service mặc định `roadwatch-web`.
- Cloud Run là evaluation/replay plane bất đồng bộ; không được đưa vào critical
  path của FCW/LDW/TTS trên edge.
- Local `Video Library` và `Upload Custom Video` đã dùng cùng API contract; Cloud
  Storage signed upload/worker là bước tiếp theo, không dùng local disk làm kho
  bền vững khi scale nhiều instance.

## Preflight (PowerShell)

```powershell
gcloud auth login
gcloud config set project c3-roadwatch-162
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com storage.googleapis.com
gcloud artifacts repositories create roadwatch --repository-format=docker --location=asia-southeast1 --description="RoadWatch images" --project=c3-roadwatch-162
gcloud storage buckets create gs://c3-roadwatch-162-roadwatch-assets --location=asia-southeast1 --uniform-bucket-level-access --project=c3-roadwatch-162
```

Lệnh tạo repository có thể báo đã tồn tại; đó là trạng thái chấp nhận được.
Billing phải được bật cho project trước khi Cloud Build/Cloud Run tạo chi phí.

## Publish model/video library (ngoài Git)

Sau khi bucket tạo thành công, upload đúng allowlist trong
`configs/cloud_assets.json`:

```powershell
gcloud storage cp roadwatch/models/yolo11n.onnx gs://c3-roadwatch-162-roadwatch-assets/models/
gcloud storage cp roadwatch/models/yolo11n.names.json gs://c3-roadwatch-162-roadwatch-assets/models/
gcloud storage cp roadwatch/models/roadwatch_detector_v2.onnx gs://c3-roadwatch-162-roadwatch-assets/models/
gcloud storage cp roadwatch/models/yolop_lane_detection_640.onnx gs://c3-roadwatch-162-roadwatch-assets/models/
gcloud storage cp roadwatch/models/roadwatch_speed_digits_v2.pt gs://c3-roadwatch-162-roadwatch-assets/models/
gcloud storage cp roadwatch/media/test_video1.mp4 gs://c3-roadwatch-162-roadwatch-assets/media/
gcloud storage cp roadwatch/media/test_video10.mp4 gs://c3-roadwatch-162-roadwatch-assets/media/
gcloud storage cp roadwatch/media/dashcam_vietnam_night.mp4 gs://c3-roadwatch-162-roadwatch-assets/media/
gcloud storage cp roadwatch/media/dashcam_vietnam_rain+night.mp4 gs://c3-roadwatch-162-roadwatch-assets/media/
```

Cloud Run tải các asset allowlist vào filesystem tạm khi khởi động. Đây là
bootstrap phù hợp demo single-instance; production cần chuyển upload custom
video sang signed GCS URL và replay worker bất đồng bộ để không phụ thuộc
filesystem của Cloud Run.

Cloud profile dùng detector/sign/lane ONNX trên CPU và không warm-up speed
classifier PyTorch; đây là trade-off cold-start cho public demo. Local/AAOS
vẫn giữ cấu hình speed classifier đầy đủ. Vì Cloud Run không có audio device,
TTS được tắt ở cloud và UI chỉ hiển thị canonical hazard/event payload.

Direct multipart upload trên Cloud Run được giới hạn 25 MB để nằm dưới giới
hạn request của service. Video dài hơn phải đi qua signed GCS resumable upload
(Phase B.2), sau đó enqueue worker; không nên nâng biến này lên 512 MB trên
public service vì platform sẽ chặn request trước khi FastAPI nhận được.

## Build và deploy

Chạy từ repository root:

```powershell
gcloud builds submit roadwatch `
  --project=c3-roadwatch-162 `
  --config=roadwatch/deploy/gcp/cloudbuild.yaml
```

Sau khi deploy, lấy URL thật:

```powershell
gcloud run services describe roadwatch-web --region=asia-southeast1 --project=c3-roadwatch-162 --format="value(status.url)"
```

`run.app` là URL fallback để test. URL khuyên dùng cho ban tổ chức là
`https://c3-roadwatch-162.io.vn`, nhưng chỉ được công bố sau khi domain owner
map DNS theo đúng record GCP cung cấp trong `UNIFIED_DEPLOYMENT_ARCHITECTURE.md`.

## Asset và giới hạn hiện tại

Dockerfile cố ý loại `models/`, `media/`, `data/`, `voices/`. Vì vậy bản deploy
không được báo là đã phân tích video thành công nếu chưa:

1. tạo bucket GCS riêng cho demo;
2. upload model đã được promotion và video library được cấp quyền;
3. triển khai asset adapter/signed upload + replay worker;
4. chạy public acceptance trên ít nhất một video mẫu và một video upload.

Không upload `.env`, credential, model/video vào Git. Khi phát triển worker,
Cloud Storage là nguồn bền vững; filesystem Cloud Run chỉ là scratch space.

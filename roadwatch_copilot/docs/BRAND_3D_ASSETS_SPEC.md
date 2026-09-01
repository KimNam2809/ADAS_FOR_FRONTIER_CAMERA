# RoadWatch — Spec tài sản 3D thương hiệu

> Phiên bản 1.0 · 2026-08-30 · Trạng thái: sẵn sàng dựng
> Bản có sơ đồ: <https://claude.ai/code/artifact/1af9e2c3-bf83-44ed-91d2-3b95326db4e1>

Ba tài sản 3D cho landing page, tài liệu kỹ thuật và slide bảo vệ. Spec này đủ chi
tiết để một người dựng 3D không biết gì về ADAS vẫn làm ra đúng thứ cần, và để lập
trình viên nối vào web mà không phải đoán tên node.

---

## 0. Nguyên tắc chi phối toàn bộ

**Đặc là thế giới. Trong suốt là suy luận.**

| Nhóm | Nội dung | Vật liệu |
|---|---|---|
| Thế giới vật lý | xe, xe máy, người, biển báo, mặt đường, vỉa hè | albedo `#2A3441`–`#6B7B8F`, rough 0.85, nhận + đổ bóng |
| Suy luận hệ thống | hình nón camera, hành lang ego, drivable area, nêm bất định, bounding box | base `#7C3AED`, alpha 0.14–0.30, emissive nhẹ, **không** đổ/nhận bóng, hiện backface |

Người xem chỉ cần ba giây để phân biệt dữ liệu thật với phỏng đoán của máy. Đó chính
là luận điểm của sản phẩm, nói bằng vật liệu thay vì bằng chữ.

> **Ràng buộc:** không dựng nội thất, logo hay ngoại hình nhận ra được của bất kỳ hãng
> xe nào, kể cả VinFast — xem `docs/VINFAST_PROJECT_TECHNICAL_DESCRIPTION.md` §9.3.
> Xe ego phải là khối sedan trung tính, không thương hiệu.

---

## 1. Hệ toạ độ và gốc

Quy ước glTF: **+Y lên**, **−Z là hướng xe chạy**, **+X bên phải người lái**.
Gốc toạ độ tại **tâm trục sau chiếu xuống mặt đất** (Y = 0). Blender làm việc Z-up;
trình xuất glTF tự chuyển, đừng xoay object thủ công.

| Thành phần | Giá trị | Ghi chú |
|---|---|---|
| Kích thước xe | 4.60 × 1.82 × 1.45 m | D×R×C, sedan cỡ C trung tính |
| Chiều dài cơ sở | 2.70 m | trục trước tại Z = −2.70 |
| Đuôi / đầu xe | Z = +1.00 / Z = −3.60 | so với gốc tại trục sau |
| Vị trí camera | (0, 1.32, −1.75) | sau kính lái, trên trục dọc |
| Góc chúc camera | −2.0° | xoay quanh X |
| FOV ngang / dọc | 60° / 36.6° | cảm biến 16:9 |
| Near / far hình nón | 1.5 m / 60 m | chỉ để dựng hình |

**Mọi khoảng cách trong tài liệu này đo từ gốc camera dọc theo −Z**, không phải từ
đầu xe. Đánh dấu bằng Empty tên `RW_REF_CAMERA_ORIGIN`.

---

## 2. ASSET 01 — Hành lang ego

*Ưu tiên cao nhất, dựng trước. Tương tác. ≤ 45k tam giác, ≤ 1.5 MB GLB.*

Cảnh chính. Người xem kéo chuột để chuyển giữa góc dashcam và góc nhìn từ trên xuống,
và thấy ngay: "nằm trong khung hình" không có nghĩa là "nằm trên đường đi của xe".

### Hình học

| Tên node | Loại | Kích thước / vị trí | Ghi chú dựng |
|---|---|---|---|
| `RW_A01_ENV_ROAD` | đặc | rộng 7.10 m · dài 60 m | X từ −5.25 đến +1.85, phẳng, Y = 0 |
| `RW_A01_ENV_SIDEWALK_L/R` | đặc | rộng 2.4 m · cao 0.14 m | hai bên, tạo mép rõ |
| `RW_A01_ENV_LANEMARK` | đặc | vạch 3.0 m, cách 6.0 m | vạch đứt tại X = −1.75 |
| `RW_A01_EGO_BODY` | đặc | 4.60 × 1.82 × 1.45 m | sedan khối, không lưới tản nhiệt, không logo |
| `RW_A01_EGO_WHEELS` | đặc | Ø 0.66 m | 4 bánh, instance của một mesh |
| `RW_A01_INF_FRUSTUM` | suy luận | 60° × 36.6° · 1.5→60 m | khối chóp cụt từ gốc camera |
| `RW_A01_INF_CORRIDOR` | suy luận | 2.6 m → 3.4 m · dài 45 m | dải phẳng, cao 0.02 m tránh z-fighting |
| `RW_A01_INF_DRIVABLE` | suy luận | phủ lòng đường | alpha thấp hơn hành lang, dừng ở mép vỉa hè |
| `RW_A01_INF_BOX_<actor>` | suy luận | bám bounding box | chỉ vẽ 8 góc dạng ngoặc |
| `RW_A01_ACT_VEH_LEAD` | đặc | X +0.15 · d 18.0 m | sedan, trong hành lang |
| `RW_A01_ACT_VEH_TRUCK` | đặc | X −3.50 · d 26.0 m | xe tải nhẹ, làn trái, ngoài hành lang |
| `RW_A01_ACT_MOTO_CUTIN` | đặc | X +1.20 · d 11.5 m · lệch −12° | xe máy + người lái, đang tạt vào |
| `RW_A01_ACT_PED_CROSSING` | đặc | X −3.90 · d 11.0 m | trong lòng đường, hướng đi +X |
| `RW_A01_ACT_PED_SIDEWALK` | đặc | X −6.20 · d 13.0 m | trên vỉa hè, ngoài drivable area |
| `RW_A01_ACT_SIGN_SPEED` | đặc | X +3.00 · Y 2.20 · d 24.0 m | biển tròn viền đỏ, số 40 |

### Bài kiểm hai người đi bộ

Hai người đi bộ nằm gần như cùng hướng nhìn từ camera, nên trong khung dashcam họ
xuất hiện sát nhau ở mé trái. Chỉ khi xoay sang góc từ trên xuống mới thấy một người
đứng trên vỉa hè và một người đang đi trong lòng đường về phía hành lang. **Đó là toàn
bộ lý do cảnh này phải là 3D.**

Sau khi đặt xong diễn viên, render thử từ `CAM_DASHCAM` và xác nhận hai người cùng nằm
ở một phần ba bên trái khung hình, kích thước chênh nhau không quá 1.6 lần. Nếu lệch,
chỉnh `d` của `PED_SIDEWALK` trong ±2 m — **đừng** chỉnh X, vì X quyết định người đó
đứng trên vỉa hè hay dưới lòng đường.

### Preset camera

Xuất kèm Empty đặt đúng transform; **không** xuất camera object của Blender.

| Tên | Vị trí (X, Y, Z) | Nhìn về | FOV dọc |
|---|---|---|---|
| `RW_A01_CAM_DASHCAM` | (0, 1.32, −1.75) | (0, 1.20, −40) | 36.6° |
| `RW_A01_CAM_TOPDOWN` | (−1.6, 34.0, −20.0) | (−1.6, 0, −20.0) | 42° |
| `RW_A01_CAM_ORBIT_HOME` | (14.5, 9.0, 6.0) | (0, 0.8, −16.0) | 38° |

Giới hạn quỹ đạo orbit trong cao độ 8°–78° để người xem không lọt xuống dưới mặt đường.

---

## 3. ASSET 02 — Nêm bất định

*Cùng GLB với Asset 01, chế độ riêng. ≤ 4k tam giác. 2 trạng thái.*

Biến giới hạn "chưa hiệu chuẩn nên không tuyên bố mét" thành thứ đáng nhớ nhất trên
trang. Một bounding box trong ảnh không map thành một điểm trên mặt đường mà thành một
nêm kéo dài theo chiều sâu.

```
Tiêu cự theo pixel
f_px = (W_ảnh / 2) / tan(FOV_ngang / 2)
     = (1920 / 2) / tan(30°) = 1662.8 px

Chiều sâu suy ra từ chiều cao box
d = f_px × H_thật / h_box

Người đi bộ, h_box = 96 px, H_thật chưa biết ∈ [1.45 m, 1.95 m]:
d ∈ [1662.8 × 1.45 / 96 , 1662.8 × 1.95 / 96]
d ∈ [25.1 m , 33.8 m]          ← nêm dài 8.7 m

Sau khi hiệu chuẩn — dùng điểm chân chạm đất thay vì chiều cao
d = h_cam / tan(θ_chúc + atan((y_chân − c_y) / f_px))
d = 29.4 m ± 1.2 m             ← nêm co lại còn một lát mỏng
```

| Tên node | Trạng thái | Hình học | Vật liệu |
|---|---|---|---|
| `RW_A02_WEDGE_RAW` | mặc định | chóp cụt trên mặt đường, d từ 25.1 → 33.8 m; bề rộng tại mỗi d = `w_box × d / f_px` | tím alpha 0.22, emissive 0.15, hai mặt |
| `RW_A02_WEDGE_CAL` | sau toggle | lát cùng tiết diện, dày 2.4 m, tâm d = 29.4 m | đỏ `#DC2626` alpha 0.34 |
| `RW_A02_RAYS` | cả hai | 4 tia từ gốc camera qua 4 góc bounding box, tới 40 m | nét mảnh 0.02 m, tím, không đổ bóng |
| `RW_A02_CONTOUR_10/20/30` | cả hai | 3 cung tròn trên mặt đường, R = 10/20/30 m từ gốc camera | tím alpha 0.4, dày 0.06 m |

> **Trung thực:** các con số 25.1 / 33.8 / 29.4 m là kết quả tính từ công thức pinhole
> với thông số camera nêu trên, **không phải** số đo thực nghiệm từ RoadWatch. Ghi rõ
> trong chú thích dưới cảnh: "ví dụ tính toán, chưa phải kết quả đo trên xe". Đúng tinh
> thần `docs/SAFETY.md`, không được bỏ.

---

## 4. ASSET 03 — Diorama giao thông hỗn hợp

*Kể chuyện, không tương tác. ≤ 60k tam giác, ≤ 1.2 MB GLB. Xoay chậm.*

Cho người chưa từng lái xe ở Việt Nam hiểu trong ba giây vì sao bài toán này khác bài
toán cao tốc Bắc Mỹ.

**Nội dung:** xe ego ở tâm (cùng khối Asset 01) · 9–12 xe máy, ít nhất 4 chiếc chở hai
người · 1 xe buýt che khuất một xe máy đang trồi ra (điểm nhấn) · 2 ô tô con, 1 xe tải
nhẹ · 5–7 người đi bộ, hai người len giữa dòng xe · vài xe máy đỗ sát mép · biển báo và
cột điện làm nền.

**Bố trí:** hình tròn bán kính 22 m quanh xe ego. Mật độ cao nhất ở dải 6–14 m — vùng
hệ thống thật sự phải ra quyết định. Không xếp thành hàng lối ngay ngắn. Điểm nhấn che
khuất tại X = −3.2 m, d = 15 m: xe buýt che gần trọn một xe máy, chỉ lộ bánh trước và
vai người lái; bố cục camera phải để chi tiết đó rơi vào một phần ba giữa khung.

Diorama này **không** vẽ lớp suy luận — không hình nón, không hành lang, không bounding
box. Nó cố tình chỉ là thế giới thật, để đặt cạnh Asset 01 thì người xem hiểu ngay lớp
suy luận đã thêm gì vào.

---

## 5. Ngân sách hình học

| Đối tượng | Tam giác tối đa | Ghi chú |
|---|---:|---|
| Xe ego | 6 000 | bánh dùng instance |
| Ô tô / xe tải | 3 500 | mỗi chiếc |
| Xe máy + người lái | 2 500 | một mesh gộp |
| Người đi bộ | 1 200 | tư thế tĩnh, không rig |
| Biển báo | 300 | mặt biển là texture 128 px |
| Đường và môi trường | 2 000 | mặt phẳng chia lưới thưa |
| Toàn bộ lớp suy luận | 4 000 | khối đơn giản, không bo góc |
| **Asset 01 tổng** | **45 000** | GLB nén Draco ≤ 1.5 MB |
| **Asset 03 tổng** | **60 000** | GLB nén Draco ≤ 1.2 MB |

---

## 6. Vật liệu — tối đa 6 slot cho cả bộ

Không texture PBR, không normal map, không AO bake. Màu đi bằng vertex color hoặc màu
base của slot. Phong cách low-poly phẳng vừa khớp ngôn ngữ "dụng cụ đo" của trang, vừa
giữ file nhỏ, vừa render mượt trên máy yếu.

| Slot | Base color | Thông số | Dùng cho |
|---|---|---|---|
| `MAT_BODY_DARK` | `#2A3441` | rough 0.85 · metal 0 | thân xe, xe máy |
| `MAT_BODY_MID` | `#6B7B8F` | rough 0.9 · metal 0 | người, xe tải, cột |
| `MAT_GROUND` | `#3A4250` | rough 1.0 · metal 0 | đường, vỉa hè |
| `MAT_EGO` | `#2563EB` | rough 0.6 · metal 0.1 | chỉ xe ego |
| `MAT_INFER` | `#7C3AED` | alpha 0.20 · emissive 0.15 · hai mặt · không bóng | toàn bộ lớp suy luận |
| `MAT_ALERT` | `#DC2626` | alpha 0.34 · emissive 0.25 | lát đã hiệu chuẩn, box critical |

---

## 7. Xuất file

```
Định dạng      glTF 2.0 Binary (.glb)
Hệ toạ độ      +Y up · −Z forward   (mặc định trình xuất glTF)
Modifier       Apply toàn bộ trước khi xuất
Camera / đèn   không xuất — chỉ xuất Empty làm mốc camera
Nén            Draco mức 7 · quantize position 14 · normal 10 · texcoord 12
Animation      không có (Asset 03 xoay bằng code, không bake)
Đặt tên        RW_<asset>_<nhóm>_<tên>  — code tìm node theo tên, đừng đổi

Bàn giao       roadwatch_a01_corridor.glb
               roadwatch_a03_diorama.glb
               /blend/*.blend            (file nguồn)
               /stills/*.png             (render 2560 px, nền trong suốt)
```

Ảnh render tĩnh dùng được ngay cho `docs/ROADWATCH_TECHNICAL_REPORT.md`, slide bảo vệ,
và làm fallback trên mobile. Dựng một lần, dùng ba chỗ.

---

## 8. Tích hợp landing page

Trang đã chạy một vòng `requestAnimationFrame` cho canvas perception 2D
(`frontend/src/landing/DashcamScene.tsx`). Thêm WebGL phải có ngân sách:

- **Chỉ một cảnh 3D trên toàn trang.** Asset 01 và 02 dùng chung renderer và GLB.
  Asset 03 nếu lên web thì thay bằng ảnh render tĩnh.
- **Lazy-load theo IntersectionObserver** — không tải GLB cho tới khi section cách
  viewport dưới 200 px.
- **Dừng vòng render** khi ra khỏi viewport và khi tab bị ẩn (`visibilitychange`).
- **Fallback tĩnh** cho màn hình < 720 px, cho `prefers-reduced-motion`, và khi
  `WebGLRenderingContext` không khả dụng.
- **Giới hạn devicePixelRatio ở 2**, giống `DashcamScene.tsx` đang làm.

Thư viện: three.js là lựa chọn hợp lý nhất. react-three-fiber nếu muốn viết kiểu React,
nhưng thêm ~150 KB gzip; hiện `frontend/package.json` chưa có dependency nhóm này.

---

## 9. Những thứ KHÔNG dựng

Danh sách này quan trọng ngang danh sách phải dựng.

- **Ô tô photoreal xoay tròn ở hero** — đắt, generic, mâu thuẫn thông điệp "chúng tôi
  nói rõ giới hạn".
- **Model VinFast VF5–VF9 hay xe có thương hiệu** — vi phạm ranh giới tuyên bố, chưa kể
  sở hữu trí tuệ.
- **"Bộ não AI" phát sáng, mạng neural 3D, hạt bay lơ lửng** — sáo mòn, không giải thích
  cơ chế nào.
- **Dựng lại sơ đồ pipeline bằng 3D** — bản SVG 2D trong `Diagrams.tsx` đọc nhanh hơn.
- **Thành phố 3D lái xuyên qua được** — chi phí lớn, và tệ hơn: khiến người xem tưởng
  đây là inference thật đang chạy.
- **Nội thất cabin chi tiết** — chưa có quyền truy cập HMI xe thật, dựng ra là ngụ ý sai.

---

## 10. Danh sách kiểm trước khi nhận bàn giao

| Hạng mục | Điều kiện đạt |
|---|---|
| Hệ toạ độ | Mở GLB trong viewer bất kỳ: xe hướng −Z, đứng trên Y = 0, không lệch gốc |
| Tên node | Đủ toàn bộ tên trong bảng Asset 01; không có `Cube.001` |
| Quy tắc vật liệu | Mọi mesh suy luận dùng `MAT_INFER` hoặc `MAT_ALERT`; không mesh đặc nào trong suốt |
| Ngân sách | Asset 01 ≤ 45k tam giác và ≤ 1.5 MB sau Draco |
| Preset camera | Ba Empty tồn tại, đúng transform, render thử khớp mô tả |
| Bài kiểm hai người đi bộ | Từ `CAM_DASHCAM` họ nằm sát nhau; từ `CAM_TOPDOWN` tách rõ trong/ngoài lòng đường |
| Z-fighting | Không nhấp nháy ở mép hành lang và drivable area khi xoay quanh cảnh |
| Ảnh tĩnh | Đủ render 2560 px từ cả ba preset, nền trong suốt |
| Không thương hiệu | Không logo, không lưới tản nhiệt nhận diện được, không biển số thật |

---

## Tài liệu nguồn

`docs/ARCHITECTURE.md` (hành lang ego, drivable area) ·
`docs/SAFETY.md` (ranh giới tuyên bố) ·
`docs/MASTER_ACTION_PLAN.md` RW-07 (hiệu chuẩn và TTC) ·
`docs/VINFAST_PROJECT_TECHNICAL_DESCRIPTION.md` §9.3 (ranh giới VinFast) ·
`frontend/src/landing/landing.css` (design token).

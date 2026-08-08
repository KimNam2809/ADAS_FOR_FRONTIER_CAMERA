#!/bin/bash
echo "=========================================================="
echo "BẮT ĐẦU ĐÁNH GIÁ MÔ HÌNH NHẬN DIỆN CHUNG (yolov10n.pt)"
echo "Sử dụng bộ dữ liệu mẫu COCO8 của Ultralytics"
echo "=========================================================="
# Ultralytics sẽ tự động tải dataset coco8.yaml (rất nhẹ) về nếu chưa có
yolo val model=models/yolov10n.pt data=coco8.yaml imgsz=640

echo ""
echo "=========================================================="
echo "BẮT ĐẦU ĐÁNH GIÁ MÔ HÌNH BIỂN BÁO (yolov10_traffic_sign.pt)"
echo "=========================================================="
# Kiểm tra xem thư mục calibration đã được copy lên server chưa
if [ -d "calibration" ]; then
    yolo val model=models/yolov10_traffic_sign.pt data=calibration/data.yaml imgsz=640
else
    echo "❌ LỖI: Không tìm thấy bộ dữ liệu 'calibration'!"
    echo "Do file quá nhiều và nặng, chúng ta đã chủ động chặn thư mục này khỏi GitHub."
    echo "Vui lòng mở Terminal trên máy Windows và chạy lệnh SCP sau để copy nó lên máy chủ:"
    echo "scp -i \"đường_dẫn_key.pem\" -r \"D:/AI_VinUni_Project_T162/SetUpModule/Object-Ditection-Manual/yolo-universal-counter/yolo-universal-counter/calibration\" ubuntu@<IP_EC2>:~/ADAS_FOR_FRONTIER_CAMERA/"
fi

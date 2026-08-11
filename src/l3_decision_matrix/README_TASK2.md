# Task 2: Actuation Dispatcher (Bộ Điều phối Phần cứng)

## Mô tả Task

**Vị trí trong hệ thống:** Ngay sau Task 1 (Arbitration Logic)  
**Mục tiêu:** Chuyển hóa priority_level thành tín hiệu vật lý giả lập tác động lên giác quan tài xế

## Hợp đồng Dữ liệu

- **Input:** priority_level từ Task 1
- **Output:** actuation_signals với audio, visual, mute_slm
- **Yêu cầu:** Phải tuân thủ nghiêm ngặt chuẩn Literal trong contracts.py

## Cấp độ Hoàn thành

### Must-have - HOÀN THÀNH
**Công nghệ:** Mapping 1-1 đơn giản  
**Quy tắc ánh xạ:**
- Priority 1: audio="urgent_beep", visual="red_overlay"
- Priority 2: audio="none", visual="yellow_overlay"
- Priority 3: audio="none", visual="green_overlay"

### Should-have - HOÀN THÀNH
**Công nghệ:** Rhythm Generator  
**Mục đích:** Tiếng beep không kêu BÍÍÍÍP kéo dài, mà xuất ra chuỗi điều khiển nhịp đứt quãng

**Triển khai:**
- 3 tiếng beep ngắn 100ms liên tiếp (100ms on, 100ms off)
- Tăng độ kích thích thính giác khẩn cấp

### Nice-to-have - CHƯA TRIỂN KHAI
**Công nghệ:** MQTT/CAN bus integration
**Lợi ích:** Sẵn sàng tích hợp thẳng vào bo mạch Raspberry Pi

## Test Cases

### TC1: Priority 1 Mapping (BẮT BUỘC ĐẬU)
- Expected: audio="urgent_beep", visual="red_overlay"
- **Result: PASS**

### TC2: Priority 2 Mapping
- **Result: PASS**

### TC3: Priority 3 Mapping
- **Result: PASS**

### TC4: Sequence Test (BẮT BUỘC ĐẬU)
- Input: priorities [3, 2, 1]
- Frame 3 Expected: {"audio": "urgent_beep", "visual": "red_overlay", "mute_slm": True}
- **Result: PASS**

### TC5: Rhythm Generator
- **Result: PASS**

**Tổng kết: 5/5 test cases PASSED**

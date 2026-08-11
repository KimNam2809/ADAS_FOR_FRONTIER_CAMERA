# Task 1: Arbitration Logic (Ma trận Phân luồng Ưu tiên)

## Mô tả Task

**Vị trí trong hệ thống:** Entry point của Tầng 3  
**Mục tiêu:** Xử lý xung đột tín hiệu (Signal Conflict)

Khi Tầng 2 phát hiện nhiều rủi ro cùng một lúc (ví dụ: xe vừa bị chệch làn LDW, vừa sắp đâm đuôi xe trước FCW), module này chịu trách nhiệm đè các tín hiệu ít nghiêm trọng hơn xuống và chỉ phát ra 1 cảnh báo sinh tử duy nhất.

## Hợp đồng Dữ liệu

- **Input:** tracked_objects[].kinematics.hazard_level, system_alerts
- **Output:** active_event (Literal), priority_level (1-3)

## Cấp độ Hoàn thành

### Must-have - HOÀN THÀNH
**Công nghệ:** Ma trận If/Else cứng  
**Quy tắc:** Nếu system_alerts.trigger_fcw == True, gán ngay priority_level = 1 và chặn lệnh kiểm tra cờ LDW

**Triển khai:**
- FCW có độ ưu tiên tuyệt đối
- Thứ tự ưu tiên: FCW > Cut-in > LDW
- Khi FCW được trigger, LDW bị bỏ qua hoàn toàn

### Should-have - HOÀN THÀNH
**Công nghệ:** Hysteresis Mechanism thông qua State Machine (FSM)  
**Mục đích:** Tránh hiện tượng tín hiệu bị nhấp nháy (Flickering) liên tục giữa Priority 1 và Priority 2 ở ranh giới TTC chập chờn 1.0 giây

**Triển khai:**
- Lock priority trong 500ms sau khi thay đổi
- Sử dụng FSM với 3 trạng thái: IDLE, LOCKED, COOLDOWN

### Nice-to-have - CHƯA TRIỂN KHAI
**Công nghệ:** Tham số hóa bộ quy tắc ưu tiên ra file YAML
**Lợi ích:** Cho phép tùy chỉnh luật ưu tiên tùy theo chế độ lái (Sport, Eco)

## Test Cases

### TC1: Xung đột FCW + LDW (BẮT BUỘC ĐẬU)
- Input: trigger_fcw=True, trigger_ldw=True
- Expected: active_event="FCW", priority_level=1
- **Result: PASS**

### TC2: Chỉ LDW
- **Result: PASS**

### TC3: Chỉ Cut-in
- **Result: PASS**

### TC4: Không cảnh báo
- **Result: PASS**

### TC5: Hysteresis
- **Result: PASS**

**Tổng kết: 5/5 test cases PASSED**

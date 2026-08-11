# Task 3: MuteSLM Logic (Cơ chế Ngắt/Khóa Audio)

## Mô tả Task

**Vị trí trong hệ thống:** Chốt chặn cuối cùng của khối actuation_signals  
**Mục tiêu:** Giải bài toán tranh chấp tài nguyên âm thanh

Đảm bảo còi báo động sinh tử (thời gian tính bằng ms) không bao giờ bị đè lên bởi câu nói dài 3 giây của LLM.

## Hợp đồng Dữ liệu

- **Input:** priority_level (từ Task 1)
- **Output:** mute_slm (boolean) trong actuation_signals

## Cấp độ Hoàn thành

### Must-have - HOÀN THÀNH
**Công nghệ:** Lệnh gán cứng  
**Quy tắc:** Nếu priority_level == 1, ép buộc mute_slm = True

**Triển khai:**
- Khi priority_level = 1, mute_slm = True ngay lập tức
- Tầng 4 sẽ check cờ này và return nếu đang phát âm thanh

### Should-have - HOÀN THÀNH
**Công nghệ:** Cooldown mechanism  
**Mục đích:** Duy trì mute sau khi thoát khỏi tình huống nguy hiểm

**Triển khai:**
- Duy trì mute_slm = True thêm 60 frames (2 giây) sau khi priority hạ từ 1 xuống
- Tài xế có thời gian ổn định trước khi AI nói

### Nice-to-have - CHƯA TRIỂN KHAI
**Công nghệ:** Signal Interrupt (Ngắt cấp hệ điều hành)
**Mục đích:** Dập tắt ngay lập tức Thread phát âm thanh của Tầng 4

## Test Cases

### TC1: Frame 121 Trigger (BẮT BUỘC ĐẬU - TỐI THIỂU)
- Frames 0-120: priority_level=3, mute_slm=False
- Frame 121: priority_level=1, mute_slm=True
- **Result: PASS**

### TC2: Cooldown Test (BẮT BUỘC ĐẬU - SHOULD-HAVE)
- Frame 100: critical (priority_level=1), mute_slm=True
- Frame 101: safe (priority_level=3), mute_slm=True (cooldown)
- Frames 100-160: mute_slm=True liên tục
- Frame 160: mute_slm=False (cooldown ends)
- **Result: PASS**

### TC3: Priority 1 Always Mutes
- **Result: PASS**

### TC4: Priority 2/3 Don't Mute
- **Result: PASS**

### TC5: State Transition
- **Result: PASS**

**Tổng kết: 5/5 test cases PASSED**

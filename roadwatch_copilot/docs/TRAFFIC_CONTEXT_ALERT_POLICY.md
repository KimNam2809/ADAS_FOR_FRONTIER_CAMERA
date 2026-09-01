# RoadWatch Traffic Context Alert Policy v1

## Mục tiêu

Giảm cảnh báo âm thanh lặp lại trong giao thông đông mà không che khuất nguy
cơ thật sự ảnh hưởng đến quỹ đạo xe. Đây là policy routing, không thay thế
object/lane/sign model và không tạo actuator command.

## Chế độ rollout

```text
ROADWATCH_TRAFFIC_CONTEXT_MODE=off       # fallback, hành vi audio hiện tại
ROADWATCH_TRAFFIC_CONTEXT_MODE=shadow    # tính và ghi telemetry, chưa đổi audio
ROADWATCH_TRAFFIC_CONTEXT_MODE=enforce   # áp dụng selective audio
```

Bản demo local mặc định chạy `enforce` thông qua `configs/default.json` và
`scripts/start.ps1`; `off` là đường fallback giữ hành vi audio cũ. Nếu context
engine ném lỗi, snapshot có `fallback=true` và governor sử dụng normal audio
policy.

## Dense mode

Chỉ đếm track đã xác nhận (`confirmed=true`, tuổi tối thiểu 0,5 giây), nằm trên
drivable area/ego lane/path corridor và không phải người rõ ràng trên vỉa hè.
Track được đếm theo `track_id`.

- Vào dense: ít nhất 8 road users, hoặc ít nhất 6 trong đó có 2 xe hai bánh,
  ổn định trong 3/5 frame inference.
- Thoát dense: dưới 5 road users liên tục 2 giây.
- Khi vào dense ở `enforce`: một event `traffic_context_attention` phát hai
  beep mềm (70 ms, nghỉ 110 ms, gain xấp xỉ 0,20), không có TTS.
- Context beep tối thiểu cách nhau 30 giây và bị bỏ qua nếu cùng thời điểm có
  threat.

## Audio routing

| Điều kiện | Kênh |
|---|---|
| FCW/VRU critical | Beep + TTS + banner đỏ |
| High-risk path conflict/lead braking/LDW mạnh | TTS + banner |
| Stop/Red Light có lane relevance | TTS + banner |
| Speed sign trong dense | HUD-only |
| Cut-in/cross-traffic rủi ro thấp | HUD-only |
| Object gần nhưng không có path conflict | HUD-only |
| Người đi bộ trên vỉa hè | Không cảnh báo |
| Turn/keep/no-turn sign | HUD-only |

Warning được xem là actionable nếu `risk_score >= 0,72`, near-field imminent,
emergency near-field, relative closing rate >= 0,30 hoặc LDW có lane quality >=
0,70 và độ lệch >= 0,45. Critical không bị hạ xuống HUD-only.

## Evidence và UI

Mỗi event có `display_scope`, `audio_route`, `context_mode` và
`suppression_reason`. Engineer Console hiển thị density score, road-user count,
two-wheeler count, low-motion ratio và audio policy. Driver HUD hiển thị context
card và tối đa ba dòng HUD-only; hazard banner chỉ dành cho event còn phạm vi
`hazard_banner`.

## Quality gate

- Non-critical audio trong dense giảm ít nhất 50% so với baseline.
- Critical recall không giảm; audio overlap = 0; pipeline error = 0.
- Context beep không quá một lần cho mỗi lần vào dense.
- Normal mode không thay đổi hành vi audio.
- E2E P95 tăng không quá 10%; display FPS giảm không quá 10%.
- Kiểm tra replay với traffic multi, night, rain+night và một video thưa.

Replay chưa có ground truth chỉ là evidence khám phá; không dùng để tuyên bố
safety validation. Human gate phải xác nhận: đông nhưng an toàn chỉ beep nhẹ +
HUD, đông có path conflict vẫn có cảnh báo, và đường thông thoáng khôi phục
normal policy.

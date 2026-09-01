from __future__ import annotations

"""Build the RoadWatch v1.2 documentary demo film.

The film is intentionally assembled from real RoadWatch captures and real
dashcam footage. Text cards are generated deterministically, narration is
Vietnamese VieNeu, and final media assembly is handled by the local FFmpeg
binary shipped with the project. No model/runtime files are changed.
"""

import json
import os
import subprocess
import sys
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT / "backend"
sys.path.insert(0, str(BACKEND))

from roadwatch.tts_vieneu import VieNeuSynthesizer  # noqa: E402


OUT = PROJECT / "output" / "demo_film_v1_2"
CARDS = OUT / "cards"
AUDIO = OUT / "audio"
SCENE_DIR = OUT / "scenes"
MEDIA = PROJECT / "media"
LANDING_MEDIA = PROJECT / "frontend" / "landing-public" / "media"
REFERENCE_VIDEO = Path(r"D:\AI_VinUni_Project_T162\Docs\Assets\202608301607 (5).mp4")
FFMPEG = PROJECT / "artifacts" / "landing-tools" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v7.1.exe"

NAVY = "#071E30"
NAVY_2 = "#0B2944"
BLUE = "#0865EB"
CYAN = "#72DAFA"
WHITE = "#FFFFFF"
MUTED = "#B8C9D7"
ORANGE = "#F5B544"


SCENE_SPECS = [
    {
        "id": "S01",
        "duration": 10,
        "kind": "video",
        "source": MEDIA / "dashcam_vietnam_traffic_multi.mp4",
        "start": 78,
        "kicker": "GIAO THÔNG VIỆT NAM",
        "title": "Nhiều xe chưa có nghĩa là nguy hiểm.",
        "narration": "Trên đường phố Việt Nam, xe máy có thể chạy rất gần. Nhưng nhìn thấy nhiều phương tiện chưa có nghĩa là đang gặp nguy hiểm.",
    },
    {
        "id": "S02",
        "duration": 14,
        "kind": "video",
        "source": MEDIA / "dashcam_vietnam_traffic_multi.mp4",
        "start": 90,
        "kicker": "BÀI TOÁN CHÚ Ý",
        "title": "Cảnh báo quá nhiều cũng trở thành vấn đề.",
        "narration": "Nếu mọi chuyển động đều trở thành một tiếng cảnh báo, tài xế sẽ phải nghe quá nhiều. Vậy điều gì thực sự cần được lên tiếng?",
    },
    {
        "id": "S03",
        "duration": 12,
        "kind": "card",
        "kicker": "GIỚI THIỆU SẢN PHẨM",
        "title": "RoadWatch Copilot",
        "body": "Trợ lý cảnh báo camera trước\nBằng tiếng Việt · hướng đến xử lý tại thiết bị",
        "footnote": "CẢNH BÁO HỖ TRỢ · KHÔNG TỰ LÁI, PHANH HAY ĐÁNH LÁI",
        "narration": "Đó là bài toán RoadWatch Copilot đang giải quyết: trợ lý cảnh báo camera trước, bằng tiếng Việt, hướng đến xử lý ngay trên thiết bị. Người lái vẫn hoàn toàn điều khiển xe.",
    },
    {
        "id": "S04",
        "duration": 14,
        "kind": "replay",
        "source": LANDING_MEDIA / "dense-replay.mp4",
        "start": 0,
        "kicker": "PIPELINE LOCAL · REPLAY",
        "title": "Nhìn thấy → theo dõi → đánh giá → chọn kênh",
        "body": "Vật thể · làn đường · biển báo\nTracking · Risk · Alert Governor",
        "footnote": "REPLAY ĐÃ GHI · KHÔNG PHẢI SUY LUẬN TRỰC TIẾP TRONG VIDEO",
        "narration": "Từ hình ảnh phía trước, RoadWatch nhận diện tác nhân giao thông, làn đường và biển báo. Hệ thống theo dõi sự thay đổi qua nhiều khung hình để đánh giá nguy cơ.",
    },
    {
        "id": "S05",
        "duration": 25,
        "kind": "ui_driver",
        "source": REFERENCE_VIDEO,
        "start": 88,
        "kicker": "DRIVER HUD · BẢN GHI THẬT",
        "title": "Thông tin ngắn, có đối tượng và vị trí.",
        "footnote": "UI DEMO RECORDED · KHÔNG KẾT LUẬN AN TOÀN TỪ MỘT ĐOẠN VIDEO",
        "narration": "Khi cần chú ý, thông tin được chuyển thành một cảnh báo ngắn, có đối tượng và vị trí. Đây là một mẫu giọng tiếng Việt của RoadWatch.",
        "product_audio": LANDING_MEDIA / "motorcycle.wav",
        "product_text": "Xe máy bên phải; giảm tốc độ.",
    },
    {
        "id": "S06",
        "duration": 18,
        "kind": "video_policy",
        "source": MEDIA / "dashcam_vietnam_traffic_multi.mp4",
        "start": 96,
        "kicker": "TRAFFIC CONTEXT V1",
        "title": "Giao thông đông không đồng nghĩa cảnh báo liên tục.",
        "body": "Nguy cơ thấp → HUD\nNguy cơ thật sự → audio ưu tiên\nCritical luôn được ưu tiên",
        "footnote": "MINH HỌA CHÍNH SÁCH · KHÔNG DÙNG VIDEO NÀY ĐỂ TUYÊN BỐ SAFETY VALIDATION",
        "narration": "RoadWatch không chỉ được thiết kế để lên tiếng. Cơ chế chọn lọc âm thanh giúp thông tin ít nguy cơ ưu tiên hiển thị, trong khi cảnh báo khẩn cấp vẫn giữ quyền ưu tiên.",
    },
    {
        "id": "S07",
        "duration": 20,
        "kind": "ui_engineer",
        "source": REFERENCE_VIDEO,
        "start": 136,
        "kicker": "ENGINEER CONSOLE · BẢN GHI THẬT",
        "title": "Mỗi cảnh báo cần có căn cứ để kiểm tra.",
        "footnote": "EVENT HISTORY · EVIDENCE · HITL · SEEKABLE TIMESTAMP",
        "narration": "Với kỹ sư, mỗi cảnh báo cần có căn cứ để kiểm tra. RoadWatch lưu lịch sử sự kiện và lý do lựa chọn kênh thông báo, giúp quay lại đúng thời điểm để tìm hiểu điều gì đã xảy ra.",
    },
    {
        "id": "S08",
        "duration": 16,
        "kind": "card_metric",
        "kicker": "MODEL PROMOTION GATE",
        "title": "Cải tiến phải được chứng minh.",
        "body": "Baseline event recall     0,80\nCandidate event recall     0,60\n\nQUYẾT ĐỊNH: GIỮ BASELINE",
        "footnote": "LOCKED REGRESSION TRONG BÁO CÁO DỰ ÁN · KHÔNG ĐẠI DIỆN MỌI TÌNH HUỐNG",
        "narration": "Chúng tôi không thay mô hình chỉ vì nó mới hơn. Trong một lần đánh giá, mô hình mới bỏ sót nhiều sự kiện hơn baseline. Vì vậy, chúng tôi giữ bản cũ. Cải tiến phải được chứng minh.",
    },
    {
        "id": "S09",
        "duration": 18,
        "kind": "card_architecture",
        "kicker": "TỪ DEMO TỚI THIẾT BỊ",
        "title": "Một lộ trình triển khai có kiểm soát.",
        "body": "LOCAL · DEMO HIỆN TẠI\n↓\nEDGE / AAOS · ĐỊNH HƯỚNG XỬ LÝ TẠI THIẾT BỊ\n↔\nCLOUD · DASHBOARD, HITL, QUẢN LÝ PHIÊN BẢN",
        "footnote": "EDGE/AAOS/CLOUD TRONG CẢNH NÀY LÀ MOCKUP ĐỊNH HƯỚNG · CHƯA OEM",
        "narration": "Hiện tại, RoadWatch được kiểm thử bằng video, có giao diện tài xế và kỹ sư. Bước tiếp theo là kiểm chứng trên phần cứng mục tiêu, phát triển giao diện trong xe và công cụ kỹ sư. Đây là định hướng cần thêm dữ liệu và thử nghiệm.",
    },
    {
        "id": "S10",
        "duration": 15,
        "kind": "card_roadmap",
        "kicker": "BƯỚC TIẾP THEO",
        "title": "Để tiến gần hơn tới xe thật",
        "body": "01  Dữ liệu có nhãn tốt hơn\n02  Phần cứng edge mục tiêu\n03  Closed-course test có kiểm soát",
        "footnote": "CHƯA CÓ CHỨNG NHẬN AN TOÀN HOẶC TÍCH HỢP OEM",
        "narration": "Để tiến gần hơn tới xe thật, chúng tôi cần dữ liệu tốt hơn, kiểm chứng trên phần cứng mục tiêu và thử nghiệm có kiểm soát.",
    },
    {
        "id": "S11",
        "duration": 8,
        "kind": "card_outro",
        "kicker": "ROADWATCH COPILOT",
        "title": "Biết khi nào cần lên tiếng.",
        "body": "Team 162 · Cohort 3\nHợp tác · Thực tập · Phát triển sản phẩm",
        "footnote": "CHỈ HỖ TRỢ CẢNH BÁO · KHÔNG TỰ LÁI",
        "narration": "Chúng tôi mong có cơ hội cùng doanh nghiệp phát triển RoadWatch, bằng những lần cải tiến có thể đo được.",
    },
]


def sh(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def ffmpeg(*args: str) -> None:
    sh([str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", *args])


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidate = Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf")
    if candidate.exists():
        return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], width: int, fnt: ImageFont.FreeTypeFont, fill: str, spacing: int = 12) -> int:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        line = ""
        for word in words:
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=fnt) > width and line:
                lines.append(line)
                line = word
            else:
                line = trial
        if line:
            lines.append(line)
    y = xy[1]
    for line in lines:
        draw.text((xy[0], y), line, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y


def base_card(scene: dict) -> Path:
    image = Image.new("RGB", (1920, 1080), NAVY)
    draw = ImageDraw.Draw(image)
    # Localized glow and structural rules, avoiding full-frame gradients.
    for r, alpha in [(560, 35), (380, 28), (220, 22)]:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse((1530 - r, 520 - r, 1530 + r, 520 + r), fill=(8, 101, 235, alpha))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)
    draw.rectangle((72, 72, 1848, 1008), outline=(22, 72, 108), width=2)
    draw.line((104, 210, 1816, 210), fill=BLUE, width=4)
    draw.text((104, 112), "ROADWATCH  /  DEMO FILM V1.2", font=font(26, True), fill=CYAN)
    draw.text((104, 270), scene.get("kicker", ""), font=font(28, True), fill=ORANGE)
    draw_wrapped(draw, scene["title"], (104, 330), 1180, font(72, True), WHITE, 18)
    body = scene.get("body")
    if body:
        draw_wrapped(draw, body, (108, 560), 1110, font(38, False), MUTED, 16)
    foot = scene.get("footnote")
    if foot:
        draw.text((108, 930), foot, font=font(22, True), fill=CYAN)
    logo = PROJECT / "data" / "assets" / "logo.png"
    if logo.exists():
        mark = Image.open(logo).convert("RGBA")
        mark.thumbnail((280, 280))
        image.paste(mark, (1510, 285), mark)
    out = CARDS / f"{scene['id']}.png"
    image.save(out)
    return out


def make_architecture_card(scene: dict) -> Path:
    path = base_card(scene)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    # Add explicit future-direction chips.
    y = 790
    chips = [("LOCAL", BLUE), ("EDGE / AAOS", (39, 145, 177)), ("CLOUD", (74, 96, 140))]
    x = 1250
    for label, color in chips:
        draw.rounded_rectangle((x, y, x + 420, y + 70), radius=18, fill=color, outline=CYAN, width=2)
        draw.text((x + 24, y + 20), label, font=font(26, True), fill=WHITE)
        x += 0
        y -= 88
    image.save(path)
    return path


def make_metric_card(scene: dict) -> Path:
    path = base_card(scene)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1225, 330, 1770, 695), radius=26, fill=(8, 38, 61), outline=CYAN, width=3)
    draw.text((1280, 385), "EVENT RECALL", font=font(26, True), fill=CYAN)
    draw.text((1280, 455), "0,80", font=font(80, True), fill=WHITE)
    draw.text((1490, 470), "baseline", font=font(25), fill=MUTED)
    draw.text((1280, 565), "0,60", font=font(80, True), fill=ORANGE)
    draw.text((1490, 580), "candidate", font=font(25), fill=MUTED)
    draw.line((1280, 535, 1710, 535), fill=(36, 78, 112), width=2)
    image.save(path)
    return path


def make_outro_card(scene: dict) -> Path:
    path = base_card(scene)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.text((104, 820), "RoadWatch Copilot", font=font(34, True), fill=WHITE)
    draw.text((104, 875), "Một trợ lý cảnh báo có thể giải thích và kiểm chứng.", font=font(25), fill=MUTED)
    image.save(path)
    return path


def make_cards() -> dict[str, Path]:
    cards: dict[str, Path] = {}
    for scene in SCENE_SPECS:
        if scene["kind"] == "card_metric":
            cards[scene["id"]] = make_metric_card(scene)
        elif scene["kind"] == "card_architecture":
            cards[scene["id"]] = make_architecture_card(scene)
        elif scene["kind"] == "card_outro":
            cards[scene["id"]] = make_outro_card(scene)
        elif scene["kind"].startswith("card"):
            cards[scene["id"]] = base_card(scene)
    return cards


def audio_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as f:
        return f.getnframes() / f.getframerate()


def synthesize_narration() -> dict[str, dict]:
    # Do not use the alert adapter for narration: its deliberate 12-word alert
    # budget is correct for driver warnings but would truncate documentary copy.
    from vieneu import Vieneu

    synthesizer = Vieneu(
        mode="v3turbo",
        backbone_repo="pnnbao-ump/VieNeu-TTS-v3-Turbo",
        device="cpu",
        backend="onnx",
        precision="int8",
    )
    result = {}
    for scene in SCENE_SPECS:
        path = AUDIO / f"{scene['id']}_narration.wav"
        generated = synthesizer.infer(scene["narration"], voice="Minh Triết")
        synthesizer.save(generated, str(path))
        result[scene["id"]] = {
            "path": str(path),
            "duration_s": round(audio_duration(path), 3),
            "provider": "vieneu/Minh Triết",
            "voice": "Minh Triết · Nam · miền Nam · tin tức",
            "voice_cloning": False,
        }
        print(f"{scene['id']}: {result[scene['id']]['duration_s']:.2f}s")
    return result


def make_video_source(scene: dict, cards: dict[str, Path]) -> Path:
    out = SCENE_DIR / f"{scene['id']}_video.mp4"
    kind = scene["kind"]
    overlay = (
        "drawbox=x=54:y=46:w=570:h=68:color=0x071E30@0.82:t=fill,"
        "drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='ROADWATCH  /  DEMO V1.2':"
        "x=78:y=67:fontsize=27:fontcolor=0x72DAFA"
    )
    if kind.startswith("card"):
        ffmpeg("-loop", "1", "-i", str(cards[scene["id"]]), "-t", str(scene["duration"]), "-r", "30", "-pix_fmt", "yuv420p", "-an", str(out))
    else:
        source = scene["source"]
        vf = f"fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{overlay}"
        ffmpeg("-ss", str(scene["start"]), "-t", str(scene["duration"]), "-i", str(source), "-vf", vf, "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out))
    return out


def make_scene_audio(scene: dict, narration: dict) -> Path:
    out = AUDIO / f"{scene['id']}_mix.wav"
    duration = scene["duration"]
    narr = narration[scene["id"]]["path"]
    product = scene.get("product_audio")
    if product:
        # Narrator starts after a short breath; product voice starts after the
        # introduction and has its own space. They never overlap.
        filt = (
            f"[0:a]adelay=500:all=1,apad,atrim=duration={duration}[n];"
            f"[1:a]adelay=8500:all=1,apad,atrim=duration={duration}[p];"
            f"[n][p]amix=inputs=2:duration=longest:dropout_transition=0,aresample=48000,volume=0.92"
        )
        ffmpeg("-i", narr, "-i", str(product), "-filter_complex", filt, "-t", str(duration), "-ac", "2", "-ar", "48000", str(out))
    else:
        filt = f"[0:a]adelay=500:all=1,apad,atrim=duration={duration},aresample=48000,volume=0.92"
        ffmpeg("-i", narr, "-filter_complex", filt, "-t", str(duration), "-ac", "2", "-ar", "48000", str(out))
    return out


def join_scenes(scene_files: list[Path]) -> Path:
    final = OUT / "RoadWatch_Demo_v1_2_1080p_yuv420p.mp4"
    trans = 0.35
    args: list[str] = []
    for scene in scene_files:
        args += ["-i", str(scene)]
    vlabels = []
    alabels = []
    elapsed = float(SCENE_SPECS[0]["duration"])
    args_filter: list[str] = []
    for i in range(len(scene_files) - 1):
        if i == 0:
            left_v, right_v = "[0:v]", "[1:v]"
            left_a, right_a = "[0:a]", "[1:a]"
        else:
            left_v, right_v = f"[v{i}]", f"[{i+1}:v]"
            left_a, right_a = f"[a{i}]", f"[{i+1}:a]"
        offset = elapsed - trans
        args_filter.append(f"{left_v}{right_v}xfade=transition=fade:duration={trans}:offset={offset:.3f}[v{i+1}]")
        args_filter.append(f"{left_a}{right_a}acrossfade=d={trans}:c1=tri:c2=tri[a{i+1}]")
        elapsed = elapsed + float(SCENE_SPECS[i + 1]["duration"]) - trans
    args += ["-filter_complex", ";".join(args_filter), "-map", f"[v{len(scene_files)-1}]", "-map", f"[a{len(scene_files)-1}]", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)]
    ffmpeg(*args)
    return final


def write_srt(narration: dict[str, dict]) -> Path:
    path = OUT / "RoadWatch_Demo_vi.srt"
    lines: list[str] = []
    cursor = 0.0
    for idx, scene in enumerate(SCENE_SPECS, 1):
        duration = min(float(narration[scene["id"]]["duration_s"]) + 0.5, scene["duration"] - 0.5)
        start = cursor + 0.5
        end = start + max(duration, 1.0)
        text = scene["narration"]
        lines += [str(idx), f"{srt_time(start)} --> {srt_time(end)}", text, ""]
        if scene.get("product_text"):
            lines += [str(idx + 100), f"{srt_time(cursor + 8.5)} --> {srt_time(min(cursor + 11.5, cursor + scene['duration'] - 0.5))}", scene["product_text"], ""]
        cursor += scene["duration"] - 0.35 if idx < len(SCENE_SPECS) else scene["duration"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    h, rem = divmod(millis, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> int:
    for folder in (OUT, CARDS, AUDIO, SCENE_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    if not FFMPEG.exists():
        raise FileNotFoundError(f"Missing FFmpeg: {FFMPEG}")
    cards = make_cards()
    narration = synthesize_narration()
    scene_files: list[Path] = []
    for scene in SCENE_SPECS:
        video = make_video_source(scene, cards)
        audio = make_scene_audio(scene, narration)
        muxed = SCENE_DIR / f"{scene['id']}.mp4"
        ffmpeg("-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(muxed))
        scene_files.append(muxed)
    final = join_scenes(scene_files)
    srt = write_srt(narration)
    manifest = {
        "film_id": "roadwatch-demo-v1.2",
        "duration_target_s": sum(s["duration"] for s in SCENE_SPECS) - 0.35 * (len(SCENE_SPECS) - 1),
        "format": {"width": 1920, "height": 1080, "fps": 30, "codec": "h264/aac"},
        "narrator": {"provider": "vieneu", "voice": "Minh Triết", "gender": "male", "region": "Nam", "voice_cloning": False},
        "source_reference_video": str(REFERENCE_VIDEO),
        "dense_demo_source": str(MEDIA / "dashcam_vietnam_traffic_multi.mp4"),
        "scenes": [{"id": s["id"], "duration_s": s["duration"], "kind": s["kind"], "source": str(s.get("source", "generated_card")), "source_start_s": s.get("start"), "narration_audio": narration[s["id"]]} for s in SCENE_SPECS],
        "truthfulness": [
            "UI captures are recorded evidence from the supplied reference video; they are not re-labelled as live cloud or AAOS proof.",
            "Edge/AAOS/Cloud are labelled future-direction mockups.",
            "No actuator command, OEM integration or safety certification is claimed.",
            "The source dashcam footage is not itself ground truth for event safety validation.",
        ],
        "outputs": {"video": str(final), "subtitles": str(srt)},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# RoadWatch Demo Film v1.2\n\n"
        "Bản dựng local từ footage RoadWatch/dashcam có provenance. Narrator: VieNeu `Minh Triết` (Nam, miền Nam); product alert voice giữ Piper.\n\n"
        "Các mockup Edge/AAOS/Cloud được gắn nhãn định hướng tương lai. Video không tuyên bố tích hợp OEM, chứng nhận an toàn hoặc khả năng tự lái.\n\n"
        f"Video: `{final.name}`\n\nPhụ đề: `{srt.name}`\n",
        encoding="utf-8",
    )
    print(f"FINAL: {final}")
    print(f"SRT: {srt}")
    print(f"MANIFEST: {OUT / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

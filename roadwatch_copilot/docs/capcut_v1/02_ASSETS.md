# Assets

Read this file before editing. Use supplied filenames, not AI substitutes.
The pack is LOCAL PREPARATION ONLY. No files have been uploaded to CapCut.
User must approve rights/privacy before transferring identifiable dashcam footage
to a third-party cloud or publicly distributing the film.

## 1. Supplied assets — no additional download needed

All paths below are relative to the extracted package. Each binary is copied
unchanged from existing RoadWatch assets; manifest.csv provides original path,
size and SHA-256. The existing clips were prepared for the landing page.

| ID | Filename | Content / provenance | Use in scene | Important constraint |
|---|---|---|---|---|
| A01 | video/A01_dense_source.mp4 | 18s of dashcam_vietnam_traffic_multi, source starts at 6s | S01/S02 | Raw context, NOT an automatically confirmed dangerous scene |
| A02 | video/A02_day_source.mp4 | 18s of test_video10, source starts at 0s | S01/S04 alternative | No inference overlay |
| A03 | video/A03_night_source.mp4 | 18s of dashcam_vietnam_night | S01/S10 alternative | Night context, not accident proof |
| A04 | video/A04_rain_source.mp4 | 18s of dashcam_vietnam_rain+night | S01/S10 alternative | Do not claim weather robustness from one clip |
| A05 | video/A05_dense_replay.mp4 | Actual local pipeline recording; 14 recorded events | S04/S06 | 12 fps capture, muted; not verified dense-mode policy success |
| A06 | video/A06_day_replay.mp4 | Actual local pipeline recording; 4 events | S04 | Detection output can contain errors |
| A07 | video/A07_night_replay.mp4 | Actual local pipeline recording; 14 events | S04 alternative | Not ground truth, no safety claim |
| A08 | video/A08_rain_replay.mp4 | Actual local pipeline recording; 5 events | S04 alternative | Not ground truth, no safety claim |
| A09 | images/A09_RoadWatch_logo.png | Original project logo | S03/S11 | Keep original artwork and proportions |
| A10 | images/A10_Driver_HUD.png | Real local UI screenshot | S03/S07/S09 | Still capture, not fabricated mouse interactions |
| A11 | images/A11_Engineer_Console.png | Real local UI screenshot | S07/S09/S10 | Numbers in screenshot are a session snapshot, not a controlled benchmark |
| A12 | audio/A12_Piper_collision.wav | “Cảnh báo va chạm”, ~0.78s | Optional alternative to S05 | Standalone product voice sample |
| A13 | audio/A13_Piper_motorcycle.wav | “Xe máy bên phải; giảm tốc độ.”, ~1.44s | S05 | Do not attach to unrelated road user/timecode |
| A14 | audio/A14_Piper_speed.wav | “Giới hạn 60 ki-lô-mét/giờ phía trước.”, ~2.17s | Optional alternative to S05 | Not proof of a visible sign at an arbitrary moment |
| A15 | evidence/A15_replay_events.json | Recorded event timeline and suppression reasons | Editor reference | Not a media file; do not narrate or display raw JSON |
| A16 | evidence/A16_runtime_benchmark.json | Historical local snapshot | Editor reference | 20s, audio off, AMD; not the export video's FPS |
| A17 | evidence/A17_technical_report.md | Existing RoadWatch technical report | S08/source checking | Supports baseline .80 vs V3 Full .60 on specified regression |

A05–A08 each have 18 seconds of encoded wall-clock replay. Preserve the original
timeline when matching event JSON; do not infer camera timing from playback fps.
None of these muted files include synchronized product audio.

## 2. Assets to record or choose — detailed shooting list

Priorities: P0 = needed for final presentation; P1 = strong improvement; P2 = optional.

| ID / priority | Create this asset | How to make it | Target | Honest fallback |
|---|---|---|---|---|
| H01 / P1 | Screen recording: select video → start → results | Run scripts/start.ps1; record actual Driver view. Use a short known clip. Capture the wait; label if trimmed. | 20–30s, 1080p, MP4 | Use A06 with “Replay đã xử lý” label; no invented clicks |
| H02 / P1 | Confirmed dense-mode demonstration | Select a dense window, ensure HUD really shows dense mode, inspect event audio routes. Record 10–15s with real policy state. | 15–25s, MP4 | Editable two-column policy diagram labelled “Minh họa chính sách” |
| H03 / P1 | Correctly synchronized hazard + TTS | Find a verified alert where object/direction/text are correct. Record system audio once, no microphone monitoring loop. Save session/timecode. | 8–12s, MP4 with audio | S05 uses a separate Piper sample card, never fakes sync |
| H04 / P1 | Engineer selects Event History and seeks | Record selecting a real row, evidence and timeline change. Keep pointer slow; no fake UI automation in editor. | 20–30s, 1080p | A11 still + explanation of supported feature |
| H05 / P2 | AAOS emulator | Open Android Studio Automotive device and actual RoadWatch app; record current behavior. | 8–12s | Labelled architecture diagram, not a manufactured emulator screenshot |
| H06 / P2 | Public web replay | Record actual URL and operation. Hide accounts/tokens/uploads. Do not claim cloud speed equals local. | 8–12s | Architecture card “Cloud: demo/đánh giá” |
| H07 / P2 | Developer reviewing evidence | Fixed camera over shoulder at 30–45°; film genuine review, no visible .env or private credentials. | 8–10s, landscape | A11 plus roadmap |
| H08 / P2 | Real team spokesperson | Eye-level medium close-up, quiet room, side light, tripod. Speak final sentence in Script. | 8–12s, landscape | Narrator over project end card; no generated person |
| H09 / P0 | Narration | Record NARRATOR lines scene by scene, or select a licensed Vietnamese voice in your editor. Do not clone someone without consent. | WAV 48kHz if possible, clean/no clipping | CapCut voice draft, human listening review before final |
| H10 / P2 | Background music | Choose an instrumental track whose license covers enterprise/promotional use and intended distribution. Save license/source. | 170s or loopable stems | No music; clean voice and intentional silence |
| H11 / P0 | End-card contact/URL | Provide real email/LinkedIn/contact and verify demo URL. Make a QR only from that real URL, scan-test it. | Editable text; optional actual QR | Show repo URL + team name, omit invented contact |

No need to buy a camera, film while driving, stage a crash or find a real VinFast
vehicle. Screen recordings plus existing footage can carry the entire draft.

## 3. Editable graphics to create directly in CapCut

These are layout instructions, not supplied finished PNG/video files.

- G01, S03: navy background, A09 logo, “RoadWatch Copilot”, warning-only subtitle.
- G02, S05: white/navy card, exact A13 transcript, small “Mẫu giọng sản phẩm”.
- G03, S06: “Ít nguy cơ → HUD” / “Khẩn cấp → cảnh báo ưu tiên”; label simulation.
- G04, S08: baseline 0,80 / V3 Full 0,60 / Giữ baseline, with regression scope footnote.
- G05, S09: Local/Edge | AAOS emulator | GCP demo. Label “Minh họa kiến trúc”.
- G06, S10: Dữ liệu có nhãn → Edge hardware → Closed-course.
- G07, S11: Logo, Team 162/Cohort 3, verified contact and warning-only guardrail.

Use editable text, not AI-rendered lettering: preserve accents and metric values.

## 4. Optional public traffic B-roll

Already-supplied RoadWatch footage is preferable for continuity. If another opening
shot is desired, a relevant public listing was found on 2026-08-31:

- [Vibrant Daytime Traffic Scene in Vietnam — Pexels](https://www.pexels.com/video/vibrant-daytime-traffic-scene-in-vietnam-33383213/)
- [Pexels official license](https://www.pexels.com/license/)

The listing is a candidate for S01/S02 only, not downloaded or inspected frame by
frame in this task. Check orientation, actual location and visible people/brands
before using. Keep the creator/asset URL, download date and a copy of the license.
Pexels permits free use and modification under its license, with restrictions;
do not assume public-domain status or imply depicted people/brands endorse RoadWatch.
Do not upload an unreviewed third-party clip to CapCut merely because it is public.

Do not use YouTube crash compilations, news clips or manufacturer advertisements
as though freely licensed. Never present stock footage as an existing customer deployment.

## 5. Upload order and review

1. Extract package. Read all three instruction files before importing media.
2. Paste 00_CAPCUT_MASTER_PROMPT.md into the main prompt.
3. If the interface accepts files, attach Script, Assets and Visual Style.
   If it only accepts text, paste their sections into the respective fields.
4. Start with A01, A06, A09–A11 and A13: a small core set avoids confusing asset assignment.
5. Add remaining context/replay clips and verified H assets as needed.
6. Keep evidence JSON/Markdown for the editor; do not upload as visual clips.
7. Approve the rough cut scene by scene: text truthfulness, video/TTS sync,
   no stretching, Vietnamese subtitles, numbers/source and missing-asset fallbacks.
8. Record real narration, replace placeholders, verify licenses/privacy/contact,
   then export. Test the final MP4 on a phone and a presentation screen.

CapCut feature names/import formats vary by account/version. These files are a
portable creative brief, not a claim that CapCut will parse every Markdown field
or deliver a correct final film automatically.

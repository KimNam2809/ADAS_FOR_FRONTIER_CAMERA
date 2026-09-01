import { useEffect, useRef, useState } from 'react';
import './landing-v1.css';

const DEMO = import.meta.env.VITE_DEMO_URL || 'https://roadwatch-web-bx6lfekcba-as.a.run.app';
const REPORT = '/documents/ROADWATCH_TECHNICAL_REPORT.md';
const REPO = 'https://github.com/AI20K-Build-Phase-Cohort-3/P-162';
const scenarios = [
  { id: 'dense', label: 'Giao thông đông', note: 'Nhiều phương tiện xuất hiện trong cùng khung hình. Chạy gần chưa đồng nghĩa với nguy hiểm.', source: 'dashcam_vietnam_traffic_multi.mp4' },
  { id: 'day', label: 'Đường ban ngày', note: 'Quan sát biển báo, phương tiện và vùng đường phía trước trong video kiểm thử.', source: 'test_video10.mp4' },
  { id: 'night', label: 'Ban đêm', note: 'Thiếu sáng có thể làm giảm chất lượng nhận diện. Đây là điều kiện cần đánh giá riêng.', source: 'dashcam_vietnam_night.mp4' },
  { id: 'rain', label: 'Mưa và thiếu sáng', note: 'Phản chiếu và vạch mờ làm thông tin làn kém chắc chắn. Hệ thống cần kiểm soát cảnh báo lệch làn.', source: 'dashcam_vietnam_rain+night.mp4' },
];
type AudioSample = { id: string; text: string; url: string; duration: number; provider: string };
type RecordedEvent = { time: number; source_time: number; event_type: string; message: string; severity: string; audio_action: string; risk_score?: number; suppression_reason?: string };
type Replay = { id: string; video: string; events: RecordedEvent[]; duration: number; source: string; models: string[] };

function useJson<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  useEffect(() => { const abort = new AbortController();
    fetch(url, { signal: abort.signal }).then(r => { if (!r.ok) throw new Error('unavailable'); return r.json(); })
      .then(setData).catch(() => {}); return () => abort.abort(); }, [url]);
  return data;
}
function Intro({ n, tag, title, children }: { n: string; tag: string; title: string; children?: React.ReactNode }) {
  return <div className="rv-intro"><p className="rv-kicker">{n} / {tag}</p><h2>{title}</h2>{children && <p className="rv-lede">{children}</p>}</div>;
}

function Explorer({ stopAudio }: { stopAudio: () => void }) {
  const [selected, setSelected] = useState('dense');
  const [time, setTime] = useState(0);
  const [failed, setFailed] = useState(false);
  const [started, setStarted] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const replays = useJson<Replay[]>('/media/replays.json');
  const scene = scenarios.find(s => s.id === selected)!;
  const replay = replays?.find(r => r.id === selected);
  const events = replay?.events || [];
  const current = [...events].reverse().find(e => e.time <= time);
  function select(id: string) { stopAudio(); video.current?.pause(); setSelected(id); setTime(0); setFailed(false); setStarted(false); }
  function seek(t: number) { stopAudio(); if (video.current) { video.current.currentTime = t; setTime(t); } }
  return <div className="rv-explorer">
    <div className="rv-choice-row" role="group" aria-label="Chọn video tình huống">{scenarios.map(s => <button key={s.id} aria-pressed={selected === s.id} onClick={() => select(s.id)}>{s.label}</button>)}</div>
    <div className="rv-explorer-grid">
      <div className="rv-player">
        <div className="rv-player-top"><span>{replay ? 'REPLAY ĐÃ XỬ LÝ' : 'VIDEO NGUỒN THỰC TẾ'}</span><span>{time.toFixed(1)}s</span></div>
        <div className="rv-video-box">
          <video key={`${selected}-${Boolean(replay)}`} ref={video} controls playsInline muted autoPlay={started} preload={started ? 'metadata' : 'none'} poster={`/media/${selected}.webp`}
            src={started ? replay?.video || `/media/${selected}.mp4` : undefined}
            onTimeUpdate={e => setTime(e.currentTarget.currentTime)} onSeeking={stopAudio} onPause={stopAudio}
            onError={() => setFailed(true)} aria-label={`Video ${scene.label}`} />
          {!started && <button className="rv-play-cover" onClick={() => { setStarted(true); stopAudio(); }}><span className="rv-play-symbol" aria-hidden="true">▶</span><span>Phát video 18 giây</span></button>}
        </div>
        {failed && <p className="rv-status" role="status">Không tải được video. Bạn vẫn có thể xem ảnh nguồn và phần giải thích. <button onClick={() => { setFailed(false); video.current?.load(); }}>Thử lại</button></p>}
        <p className="rv-caption">{replay ? 'Kết quả ghi từ pipeline local ở 12 frame/giây, đã tắt âm thanh. Không suy luận trực tiếp trong trang này.' : 'Video nguồn chưa có overlay phân tích. Phần chính sách bên dưới là minh họa độc lập.'} Không phải chứng nhận an toàn.</p>
      </div>
      <aside className="rv-evidence-panel"><p className="rv-kicker">ĐỌC TÌNH HUỐNG</p><h3>{scene.label}</h3><p>{scene.note}</p>
        <div className="rv-source">Nguồn video<span>{scene.source}</span></div>
        <div className="rv-event-readout"><span className="rv-label">Sự kiện đã ghi gần nhất</span><strong>{current?.message || (replay ? 'Chưa có sự kiện tại mốc này.' : 'Chưa có evidence replay cho clip này.')}</strong>
          {current && <dl><div><dt>Loại</dt><dd>{current.event_type}</dd></div><div><dt>Kênh dự kiến</dt><dd>{current.audio_action}</dd></div><div><dt>Lý do hạn chế</dt><dd>{current.suppression_reason || '—'}</dd></div><div><dt>Video nguồn</dt><dd>{current.source_time.toFixed(1)}s</dd></div></dl>}</div>
        <p className="rv-small">Chọn mốc để tua và kiểm tra. Câu cảnh báo giữ nguyên output của pipeline, kể cả khi cần xem xét lại.</p>
        <div className="rv-event-list">{events.map((e, i) => <button key={i} disabled={!started} onClick={() => seek(e.time)}><span>{e.time.toFixed(1)}s</span>{e.message}</button>)}</div>
      </aside>
    </div>
  </div>;
}

function Policy({ stopAudio }: { stopAudio: () => void }) {
  const [dense, setDense] = useState(true);
  const [risk, setRisk] = useState<'low' | 'high' | 'critical'>('low');
  const route = risk === 'critical' ? 'BEEP + TTS + HAZARD' : risk === 'high' ? 'TTS + HAZARD' : dense ? 'HUD-ONLY' : 'GOVERNOR THÔNG THƯỜNG';
  return <div className="rv-policy"><div><p className="rv-kicker">MINH HỌA CHÍNH SÁCH · KHÔNG ĐỔI NGƯỠNG THẬT</p>
    <h3>Không phải điều gì nhìn thấy<br />cũng cần đọc thành tiếng.</h3>
    <p>Thay đổi ngữ cảnh để hiểu cách chọn kênh cảnh báo. Các mức dưới đây là tình huống minh họa, không phải dự đoán từ video đang xem.</p>
    <label className="rv-switch"><input type="checkbox" checked={dense} onChange={e => { stopAudio(); setDense(e.target.checked); }} />Giao thông mật độ cao</label>
    <div className="rv-choice-row" role="group" aria-label="Chọn mức nguy cơ">{[['low','Ít nguy cơ'],['high','Xung đột rõ'],['critical','Khẩn cấp']].map(([id,label]) => <button key={id} aria-pressed={risk === id} onClick={() => { stopAudio(); setRisk(id as typeof risk); }}>{label}</button>)}</div>
  </div><div className={`rv-route rv-route-${risk}`} aria-live="polite"><span className="rv-label">KÊNH CẢNH BÁO ĐỀ XUẤT</span><strong>{route}</strong><p>{risk === 'critical' ? 'Cảnh báo khẩn cấp giữ quyền ưu tiên. Giao thông đông không được làm mất cảnh báo nguy hiểm.' : risk === 'high' ? 'Khi nguy cơ thực sự ảnh hưởng đường đi của xe, âm thanh vẫn được ưu tiên.' : dense ? 'Thông tin ít nguy cơ chuyển lên HUD. Khi mới vào dense mode, có thể phát một lần hai beep nhẹ nếu không có cảnh báo ưu tiên.' : 'Trở về chính sách hiện tại: temporal confirmation, cooldown và audio budget. Không phải mọi đối tượng đều tạo cảnh báo.'}</p><span className="rv-chip">Deterministic · có lý do · có fallback</span></div></div>;
}

const steps = [
  ['01', 'Nhìn', 'Perception', 'Ba nhánh riêng: tác nhân giao thông, biển báo và làn/vùng có thể đi. Mỗi nhánh có health và profile để rollback.', 'YOLO11n · Sign v2 · YOLOP'],
  ['02', 'Theo dõi', 'Tracking', 'Liên kết đối tượng qua nhiều frame, giữ track ID, vị trí và lịch sử thay đổi. Một box đơn lẻ chưa đủ để kết luận nguy hiểm.', 'Track ID · temporal evidence'],
  ['03', 'Đánh giá', 'Risk engine', 'Ước lượng xung đột đường đi và xu hướng tiếp cận trong ảnh. Chưa có calibration/CAN thì không coi đó là khoảng cách hoặc tốc độ vật lý.', 'FCW · VRU · cut-in · cross-traffic · LDW'],
  ['04', 'Chọn lọc', 'Traffic Context + Governor', 'Kết hợp mức nguy hiểm, mật độ, temporal confirmation, cooldown và lane relevance để chọn cảnh báo phù hợp.', 'Critical priority · selective audio'],
  ['05', 'Cảnh báo', 'Canonical event + Piper', 'Banner và giọng đọc dùng cùng nội dung sự kiện. Một audio owner giúp tránh hai luồng phát tiếng chồng nhau.', 'HUD · beep · TTS tiếng Việt'],
  ['06', 'Kiểm chứng', 'Evidence + HITL', 'Kỹ sư xem lịch sử, risk, confidence và lý do suppress. SLM optional giải thích cho kỹ sư, không quyết định cảnh báo khẩn cấp.', 'Event History · metrics · audit'],
];
function Technology() {
  const [step, setStep] = useState(0);
  return <><div className="rv-step-tabs" role="group" aria-label="Khám phá pipeline">{steps.map((s,i) => <button key={s[0]} aria-pressed={step === i} onClick={() => setStep(i)}><span>{s[0]}</span>{s[1]}</button>)}</div><div className="rv-step-detail" aria-live="polite"><span className="rv-step-number">{steps[step][0]}</span><div><p className="rv-kicker">{steps[step][2]}</p><h3>{steps[step][4]}</h3><p>{steps[step][3]}</p></div></div></>;
}

function Tour() {
  const [role, setRole] = useState('driver');
  const [feature, setFeature] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);
  const points = role === 'driver' ? [
    ['HUD phía trước', 'Trực quan hóa phương tiện và trạng thái cảnh báo từ cùng pipeline. Tốc độ mô phỏng không phải tốc độ thật của xe.'],
    ['Một cảnh báo rõ ràng', 'Hazard và TTS lấy cùng canonical event. Nguy cơ cao có quyền ưu tiên âm thanh.'],
    ['Điều khiển video', 'Pause, tua và đổi video phục vụ kiểm thử. Đây là demo replay, không phải điều khiển xe.'],
  ] : [
    ['Event History', 'Chọn sự kiện để xem evidence và quay lại mốc video cần kiểm tra.'],
    ['Metrics có điều kiện đo', 'Processed FPS, Display FPS và E2E latency là các phép đo khác nhau; không dùng FPS hiển thị làm FPS inference.'],
    ['HITL và SLM', 'Kỹ sư cấu hình ngưỡng và đánh giá output. SLM bổ sung giải thích bất đồng bộ và có fallback deterministic.'],
  ];
  return <><div className="rv-choice-row" role="group" aria-label="Vai trò người dùng">{['driver','engineer'].map(r => <button key={r} aria-pressed={role === r} onClick={() => { setRole(r); setFeature(0); setImageFailed(false); }}>{r === 'driver' ? 'Driver HUD' : 'Engineer Console'}</button>)}</div><div className="rv-tour"><div className="rv-tour-image">
    {!imageFailed ? <a className="rv-capture-link" href={`/media/${role}-capture.webp`} target="_blank" rel="noreferrer" aria-label={`Mở ảnh ${role} đầy đủ`}><img key={role} src={`/media/${role}-capture.webp`} loading="lazy" width="1440" height="990" alt={`Ảnh chụp phiên local ${role === 'driver' ? 'Driver HUD' : 'Engineer Console'}`} onError={() => setImageFailed(true)} /></a> : <div className="rv-tour-fallback"><h3>{role === 'driver' ? 'Driver HUD' : 'Engineer Console'}</h3><p>Ảnh phiên local chưa được tạo. Mở app để trải nghiệm giao diện hiện tại.</p><a className="rv-btn" href={DEMO}>Mở ứng dụng</a></div>}
    <p className="rv-caption">Ảnh chụp phiên kiểm thử local · giao diện và dữ liệu có thể khác khi đổi video.</p></div><div className="rv-tour-notes">{points.map(([label,desc],i) => <button key={label} aria-expanded={feature === i} onClick={() => setFeature(i)}><span className="rv-label">0{i + 1}</span><strong>{label}</strong>{feature === i && <p>{desc}</p>}</button>)}</div></div></>;
}

type Benchmark = { date: string; source: string; seconds: number; hardware: string; audio: string; metrics: { processed_fps: number; display_fps: number; latencies?: { end_to_end?: {p50_ms: number; p95_ms: number} } } };
function Evidence() {
  const [group, setGroup] = useState('runtime');
  const data = useJson<Benchmark>('/media/benchmark.json');
  const metrics = data?.metrics;
  const cards = group === 'runtime' ? [
    [metrics?.processed_fps?.toFixed(2) || '—', 'Processed FPS', 'Frame thực sự qua inference/risk'],
    [metrics?.display_fps?.toFixed(2) || '—', 'Display FPS', 'Frame được mã hóa để hiển thị'],
    [metrics?.latencies?.end_to_end?.p95_ms?.toFixed(2) || '—', 'E2E P95 · ms', 'Snapshot replay; không phải độ trễ mạng'],
  ] : group === 'sign' ? [['0.98741','Sign mAP50','Metric riêng cho detector biển báo'],['0.83217','Sign mAP50–95','Không phải accuracy toàn hệ thống'],['0.98254','Speed top-1','Metric riêng cho classifier tốc độ']] : [['0.80','Baseline event recall','Trên locked regression được công bố'],['0.60','V3 Full event recall','Candidate chưa được promote'],['Giữ baseline','Quyết định release','Ưu tiên event recall, không chỉ mAP']];
  return <><div className="rv-choice-row" role="group" aria-label="Nhóm bằng chứng">{[['runtime','Runtime local'],['sign','Biển báo'],['model','Model promotion']].map(([id,label]) => <button key={id} aria-pressed={group === id} onClick={() => setGroup(id)}>{label}</button>)}</div><div className="rv-metrics">{cards.map(([value,label,desc]) => <div key={label}><strong>{value}</strong><h3>{label}</h3><p>{desc}</p></div>)}</div>
    <div className="rv-measure-note"><p>{group === 'runtime' ? (data ? `Nguồn JSON benchmark · ${data.date.slice(0,10)} · ${data.hardware} · ${data.source} · ${data.seconds}s · audio ${data.audio}.` : 'Chưa tải được báo cáo; không thay số liệu thiếu bằng số 0.') : 'Snapshot nghiên cứu từ báo cáo kỹ thuật. Các metric khác nhau không được gộp thành một tỷ lệ “chính xác RoadWatch”.'}<br />Kết quả phụ thuộc video, model và thiết bị. Chưa phải chứng nhận an toàn hoặc benchmark Jetson thật.</p><a href={group === 'runtime' ? '/media/benchmark.json' : REPORT} target="_blank" rel="noreferrer">Xem nguồn số liệu ↗</a></div></>;
}

function Deployment() {
  const [tab,setTab] = useState(0);
  const items = [
    ['Local / Edge', 'Cảnh báo trên thiết bị.', 'Video hoặc camera → perception → risk → HUD/TTS local.', 'Khi model, voice và UI đã tải đầy đủ, đường xử lý local không cần cloud. Jetson Orin là đích triển khai cần benchmark phần cứng thật.'],
    ['AAOS', 'Một giao diện trong xe.', 'Nguồn replay → RoadWatch core → HMI Android Automotive.', 'Hiện kiểm thử trên Android Studio emulator. Chưa truy cập camera hoặc CAN của VinFast; cần OEM cung cấp API và quyền tích hợp.'],
    ['GCP', 'Để mọi người cùng kiểm chứng.', 'Browser → upload/chọn video → cloud replay → kết quả.', 'Public demo là môi trường đánh giá. Có cold start, truyền video và độ trễ mạng; không dùng cloud demo làm đường cảnh báo khẩn cấp trên xe.'],
  ];
  return <><div className="rv-choice-row" role="group" aria-label="Môi trường triển khai">{items.map((s,i)=><button key={s[0]} aria-pressed={tab===i} onClick={()=>setTab(i)}>{s[0]}</button>)}</div><div className="rv-deployment" aria-live="polite"><span className="rv-big-label">{items[tab][0]}</span><div><h3>{items[tab][1]}</h3><p className="rv-flow">{items[tab][2]}</p><p>{items[tab][3]}</p></div></div></>;
}

const faq = [
  ['RoadWatch có tự lái hoặc tự phanh không?', 'Không. RoadWatch chỉ cảnh báo/hỗ trợ; không có lệnh điều khiển ga, phanh hoặc đánh lái. Người lái luôn chịu trách nhiệm.'],
  ['Các video trên landing có chạy AI trực tiếp không?', 'Không. Video nguồn và replay đã xử lý được gắn nhãn riêng. Tương tác chính sách là minh họa. Hãy mở ứng dụng demo để phân tích video thực sự.'],
  ['Tại sao hệ thống có lúc không phát tiếng?', 'Alert Governor và Traffic Context lọc cảnh báo lặp, ít nguy cơ hoặc chưa chắc chắn. Giao thông đông ưu tiên HUD cho thông tin nhẹ; nguy cơ critical vẫn có quyền ưu tiên. Model vẫn có thể bỏ sót hoặc nhận sai.'],
  ['Có thể dùng trên xe VinFast ngay không?', 'Chưa. Cần camera API, quyền OEM, calibration, telemetry nếu dùng và thử nghiệm closed-course. AAOS emulator chứng minh HMI/contract, không chứng minh đã tích hợp xe thật.'],
  ['Có chạy offline không?', 'Core local được thiết kế chạy offline sau khi chuẩn bị model, voice và UI. Website GCP cần mạng và không thay thế core trên thiết bị.'],
  ['Tôi có thể thử video của mình ở đâu?', 'Bấm Mở demo phân tích video, đăng nhập vai trò phù hợp, rồi chọn hoặc upload trong app. Chỉ dùng video bạn có quyền sử dụng; cloud có thể cần thời gian khởi động.'],
];

export default function LandingV1() {
  const [menu,setMenu] = useState(false);
  const [playing,setPlaying] = useState<string | null>(null);
  const [audioError,setAudioError] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const claim = useRef(0);
  const audioSamples = useJson<AudioSample[]>('/media/audio.json');
  const root = useRef<HTMLDivElement>(null);
  function stopAudio() { claim.current++; audioRef.current?.pause(); if (audioRef.current) audioRef.current.currentTime=0; setPlaying(null); }
  async function play(sample: AudioSample) {
    if (playing===sample.id) { stopAudio(); return; }
    stopAudio(); setAudioError(''); const token=claim.current;
    const audio = audioRef.current || new Audio(); audioRef.current=audio;
    audio.src=sample.url; audio.onended=()=>{ if(token===claim.current)setPlaying(null); };
    audio.onerror=()=>{ if(token===claim.current){setPlaying(null);setAudioError('Không phát được WAV. Nội dung câu vẫn hiển thị bên dưới.');} };
    setPlaying(sample.id);
    try { await audio.play(); } catch { if(token===claim.current){setPlaying(null);setAudioError('Trình duyệt chưa cho phép âm thanh hoặc WAV chưa sẵn sàng. Bấm nghe để thử lại.');} }
  }
  useEffect(()=>{ const visibility=()=>{if(document.hidden)stopAudio();};const pagehide=()=>stopAudio();document.addEventListener('visibilitychange',visibility);window.addEventListener('pagehide',pagehide);
    return ()=>{audioRef.current?.pause();document.removeEventListener('visibilitychange',visibility);window.removeEventListener('pagehide',pagehide);};},[]);
  useEffect(()=>{const el=root.current;if(!el||!('IntersectionObserver' in window))return;
    const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('rv-visible');observer.unobserve(e.target);}}),{threshold:0.08});
    el.querySelectorAll('[data-reveal]').forEach(e=>observer.observe(e));return()=>observer.disconnect();},[]);
  return <div className="rv" ref={root}>
    <a className="rv-skip" href="#main">Bỏ qua điều hướng</a>
    <header className="rv-header"><a className="rv-brand" href="#top"><img src="/media/logo.webp" alt="" width="38" height="38" />RoadWatch<span>COPILOT</span></a>
      <nav aria-label="Điều hướng chính" className={menu?'rv-nav rv-nav-open':'rv-nav'}>{[['#experience','Trải nghiệm'],['#technology','Công nghệ'],['#evidence','Bằng chứng'],['#faq','Giải đáp']].map(([url,label])=><a key={url} href={url} onClick={()=>setMenu(false)}>{label}</a>)}</nav>
      <a className="rv-btn rv-btn-small" href={DEMO}>Mở demo <span aria-hidden="true">↗</span></a><button className="rv-menu" aria-expanded={menu} aria-label="Mở menu" onClick={()=>setMenu(!menu)}>Menu</button></header>
    <main id="main">
      <section className="rv-hero" id="top"><div className="rv-wrap"><div className="rv-hero-heading"><p className="rv-kicker">EDGE INTELLIGENCE / GIAO THÔNG VIỆT NAM</p><h1>Hiểu điều phía trước.<br /><span>Nhắc điều cần chú ý.</span></h1><div className="rv-hero-bottom"><p>Trợ lý cảnh báo hỗ trợ lái bằng tiếng Việt.<br />Nhìn tình huống, chọn ưu tiên và biết khi nào nên im lặng.</p><a className="rv-btn rv-btn-white" href="#experience">Trải nghiệm tình huống <span aria-hidden="true">↓</span></a></div></div>
      <a href="#experience" className="rv-hero-visual" aria-label="Xem video giao thông thực tế"><img src="/media/dense.webp" alt="Khung hình camera phía trước trong video giao thông Việt Nam" width="960" height="540" fetchPriority="high" /><div className="rv-visual-top"><span>ROADWATCH / FORWARD VIEW</span><span>VIDEO REPLAY</span></div><div className="rv-visual-bottom"><span className="rv-play-round" aria-hidden="true">▶</span><div><strong>Không chỉ nhìn thấy phương tiện.</strong><p>Hiểu điều gì cần được cảnh báo.</p></div><span className="rv-visual-index">01 — 04</span></div></a>
      <div className="rv-hero-foot"><span>Prototype · Video replay · Warning-only</span><span>Không tự lái. Không tự phanh. Người lái luôn quyết định.</span></div></div></section>
      <section className="rv-section rv-wrap rv-problem" data-reveal><p className="rv-kicker">BÀI TOÁN</p><h2>Đông xe.<br /><span>Không đồng nghĩa nguy hiểm.</span></h2><div><p className="rv-lede">Trong giao thông hỗn hợp, một tiếng beep cần có lý do. Xe máy chạy gần, người đi bộ bên đường hay một biển báo xa chưa chắc cần chiếm sự chú ý của tài xế.</p><p>RoadWatch kết hợp nhận diện, bằng chứng qua nhiều khung hình và chính sách ưu tiên — để cảnh báo có đối tượng, vị trí và ngữ cảnh.</p><div className="rv-facts"><span><b>03</b>Nhánh perception</span><span><b>02</b>Vai trò sử dụng</span><span><b>01</b>Luồng cảnh báo chung</span></div></div></section>
      <section className="rv-section rv-soft" id="experience"><div className="rv-wrap"><Intro n="01" tag="TỰ MÌNH KHÁM PHÁ" title="Một tình huống. Nhiều điều để hiểu.">Chọn video, tua đến sự kiện và xem bằng chứng. Preview này không gọi model hoặc gửi video của bạn lên cloud.</Intro><Explorer stopAudio={stopAudio}/></div></section>
      <section className="rv-section rv-wrap" id="context" data-reveal><Policy stopAudio={stopAudio}/></section>
      <section className="rv-section rv-dark" id="voice"><div className="rv-wrap rv-voice"><Intro n="02" tag="GIỌNG NÓI CÓ NGỮ CẢNH" title="Nghe rõ. Hiểu nhanh.">Tiếng Việt từ Piper release hiện tại. Bấm để nghe từng câu mẫu; không tự phát âm thanh khi cuộn trang.</Intro><div className="rv-voice-samples">{audioSamples ? audioSamples.map(s=><button key={s.id} className={playing===s.id?'rv-sample rv-sample-active':'rv-sample'} onClick={()=>play(s)} aria-pressed={playing===s.id}><span className="rv-label">{s.id==='collision'?'FCW / KHẨN CẤP':s.id==='motorcycle'?'VRU / XE MÁY':'BIỂN TỐC ĐỘ'}</span><strong>{s.text}</strong><span className="rv-sample-action">{playing===s.id?'■ Dừng':'▶ Nghe mẫu'} · {s.duration}s</span></button>):<p className="rv-status">Audio mẫu chưa sẵn sàng. Chạy bước chuẩn bị media để nghe Piper.</p>}<p className="rv-small">Piper vi_VN-vais1000-medium · “Trúc Ly” là tên hiển thị của release RoadWatch.</p>{audioError&&<p role="status">{audioError}</p>}</div></div></section>
      <section className="rv-section rv-wrap" id="people" data-reveal><Intro n="03" tag="HAI GÓC NHÌN, CÙNG MỘT SỰ KIỆN" title="Rõ ràng cho tài xế. Có cơ sở cho kỹ sư.">Driver tập trung vào tình huống. Engineer kiểm tra vì sao cảnh báo xuất hiện, và điều gì cần cải thiện.</Intro><Tour/></section>
      <section className="rv-section rv-soft" id="technology"><div className="rv-wrap"><Intro n="04" tag="BÊN TRONG ROADWATCH" title="Từ hình ảnh đến quyết định cảnh báo.">Mỗi tầng có trách nhiệm rõ ràng. SLM không nằm trong đường quyết định khẩn cấp.</Intro><Technology/></div></section>
      <section className="rv-section rv-wrap" id="deployment" data-reveal><Intro n="05" tag="MỘT CORE, NHIỀU MÔI TRƯỜNG" title="Thiết kế cho edge. Mở để kiểm chứng.">Chọn môi trường để hiểu phần nào đang chạy và phần nào cần thêm bằng chứng triển khai.</Intro><Deployment/></section>
      <section className="rv-section rv-dark" id="evidence"><div className="rv-wrap"><Intro n="06" tag="KỸ THUẬT CẦN BẰNG CHỨNG" title="Con số đi cùng điều kiện đo.">Phân biệt chất lượng model, chất lượng cảnh báo và hiệu năng hệ thống. Không gộp thành một tỷ lệ chính xác duy nhất.</Intro><Evidence/></div></section>
      <section className="rv-section rv-wrap" id="safety" data-reveal><div className="rv-safety"><p className="rv-kicker">RANH GIỚI AN TOÀN</p><h2>Người lái luôn<br />là người quyết định.</h2><p className="rv-lede">RoadWatch là prototype hỗ trợ cảnh báo. Chất lượng còn phụ thuộc model, dữ liệu và điều kiện quan sát.</p><div className="rv-roadmap"><div><span className="rv-label">ĐANG CÓ</span><p>Video replay · HUD · TTS · Traffic Context · Evidence</p></div><div><span className="rv-label">ĐANG ĐÁNH GIÁ</span><p>Perception candidate · Night/rain · SLM optional</p></div><div><span className="rv-label">CẦN KIỂM CHỨNG THỰC ĐỊA</span><p>Calibration · Camera/OEM API · Jetson · Closed-course</p></div></div></div></section>
      <section className="rv-section rv-soft" id="faq"><div className="rv-wrap rv-faq"><Intro n="07" tag="HIỂU ĐÚNG SẢN PHẨM" title="Trước khi bắt đầu.">Những câu hỏi nên đặt ra với một dự án ADAS.</Intro><div>{faq.map(([q,a])=><details key={q}><summary>{q}</summary><p>{a}</p></details>)}</div></div></section>
      <section className="rv-section rv-wrap rv-final"><p className="rv-kicker">ROADWATCH COPILOT · TEAM 162 / COHORT 3</p><h2>Đừng chỉ xem.<br /><span>Hãy tự kiểm chứng.</span></h2><p>Chọn video có sẵn hoặc upload trong ứng dụng demo.<br />Cloud có thể cần khởi động; local vẫn là đường kiểm thử độc lập.</p><div className="rv-actions"><a className="rv-btn" href={DEMO}>Mở demo phân tích video ↗</a><a className="rv-btn rv-btn-outline" href={REPORT} download>Đọc báo cáo kỹ thuật ↓</a></div></section>
    </main><footer className="rv-footer rv-wrap"><div className="rv-brand"><img src="/media/logo.webp" width="32" height="32" alt=""/>RoadWatch</div><span>Landing v1.0 · 30.08.2026 · Local preview</span><a href={REPO} target="_blank" rel="noreferrer">Source code ↗</a><a href="#safety">Giới hạn an toàn</a></footer>
  </div>;
}

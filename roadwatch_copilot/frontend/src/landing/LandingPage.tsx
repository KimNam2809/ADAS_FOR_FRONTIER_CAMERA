import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DashcamScene, { GATE_ORDER, TRACE_MARKS, type SceneState, type Scenario } from "./DashcamScene";
import { LatencyChart, PipelineDiagram } from "./Diagrams";
import { BENCH_CONDITIONS, COPY, EVIDENCE, LANGS, SPEC_ROWS, type Lang } from "./content";
import "./landing.css";

/* ------------------------------------------------------------------ */
/* Hooks nhỏ                                                           */
/* ------------------------------------------------------------------ */

function useReveal() {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const root = ref.current;
    if (!root || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add("rw-in");
            io.unobserve(e.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    root.querySelectorAll(".rw-reveal").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return ref;
}

function useStuckNav() {
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return stuck;
}

function useLang(initial: Lang): [Lang, (l: Lang) => void] {
  const [lang, setLang] = useState<Lang>(() => {
    try {
      const saved = window.localStorage.getItem("roadwatch_landing_lang");
      if (saved === "vi" || saved === "en") return saved;
    } catch { /* storage có thể bị chặn */ }
    return initial;
  });
  const set = useCallback((next: Lang) => {
    setLang(next);
    try { window.localStorage.setItem("roadwatch_landing_lang", next); } catch { /* bỏ qua */ }
  }, []);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  return [lang, set];
}

/**
 * Beep tổng hợp bằng Web Audio theo đúng thông số trong
 * docs/TRAFFIC_CONTEXT_ALERT_POLICY.md: xung 70 ms, nghỉ 110 ms.
 * Chỉ khởi tạo AudioContext sau khi người dùng bấm bật — không bao giờ tự phát.
 */
function useBeep(enabled: boolean) {
  const ctxRef = useRef<AudioContext | null>(null);
  useEffect(() => {
    if (!enabled) {
      ctxRef.current?.close().catch(() => undefined);
      ctxRef.current = null;
    }
    return () => { ctxRef.current?.close().catch(() => undefined); };
  }, [enabled]);

  return useCallback((severity: "critical" | "warning" | "advisory" | "context") => {
    if (!enabled) return;
    type Ctor = typeof AudioContext;
    const Ctx: Ctor | undefined = window.AudioContext
      ?? (window as unknown as { webkitAudioContext?: Ctor }).webkitAudioContext;
    if (!Ctx) return;
    const ac = ctxRef.current ?? (ctxRef.current = new Ctx());
    if (ac.state === "suspended") void ac.resume();

    const spec = {
      critical: { pulses: 3, freq: 1180, gain: 0.34 },
      warning: { pulses: 2, freq: 940, gain: 0.24 },
      advisory: { pulses: 1, freq: 760, gain: 0.18 },
      context: { pulses: 2, freq: 620, gain: 0.2 },
    }[severity];

    for (let i = 0; i < spec.pulses; i++) {
      const at = ac.currentTime + i * 0.18;          // 70 ms xung + 110 ms nghỉ
      const osc = ac.createOscillator();
      const g = ac.createGain();
      osc.type = "sine";
      osc.frequency.value = spec.freq;
      g.gain.setValueAtTime(0.0001, at);
      g.gain.exponentialRampToValueAtTime(spec.gain, at + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, at + 0.07);
      osc.connect(g).connect(ac.destination);
      osc.start(at);
      osc.stop(at + 0.09);
    }
  }, [enabled]);
}

function useScrollProgress() {
  const [pct, setPct] = useState(0);
  useEffect(() => {
    const on = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setPct(max > 0 ? Math.min(100, (window.scrollY / max) * 100) : 0);
    };
    on();
    window.addEventListener("scroll", on, { passive: true });
    window.addEventListener("resize", on);
    return () => { window.removeEventListener("scroll", on); window.removeEventListener("resize", on); };
  }, []);
  return pct;
}

const Logo = () => (
  <span className="rw-logo">
    <span className="rw-logo-mark" aria-hidden="true"><span /></span>
    RoadWatch
  </span>
);

/* ------------------------------------------------------------------ */
/* Trang                                                               */
/* ------------------------------------------------------------------ */

export interface LandingPageProps {
  /** Mặc định "vi". */
  defaultLang?: Lang;
  /** Link "Xem demo" — mặc định trỏ về gốc ứng dụng HMI. */
  demoHref?: string;
  /** Truyền "/api/stream.mjpg" để hiển thị pipeline thật thay vì mô phỏng. */
  streamUrl?: string;
}

export default function LandingPage({ defaultLang = "vi", demoHref = "/", streamUrl }: LandingPageProps) {
  const [lang, setLang] = useLang(defaultLang);
  const t = COPY[lang];
  const stuck = useStuckNav();
  const revealRef = useReveal();

  const [menuOpen, setMenuOpen] = useState(false);
  const [scenario, setScenario] = useState<Scenario>("day");
  const [playing, setPlaying] = useState(true);
  const [scene, setScene] = useState<SceneState | null>(null);
  const [scnTab, setScnTab] = useState(0);
  const [cond, setCond] = useState("day");
  const [sound, setSound] = useState(false);
  const [seek, setSeek] = useState<number | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState("");
  const progress = useScrollProgress();
  const beep = useBeep(sound);
  const beepRef = useRef(beep);
  beepRef.current = beep;
  const lastAlertRef = useRef<string | null>(null);

  const onSceneState = useCallback((s: SceneState) => {
    setScene(s);
    const key = s.alert ? `${s.alert.id}:${Math.floor(s.time)}` : null;
    if (s.alert && s.alert.route !== "hud") {
      const id = s.alert.id;
      if (lastAlertRef.current !== id) {
        lastAlertRef.current = id;
        beepRef.current?.(s.alert.severity);
      }
    } else if (!s.alert) {
      lastAlertRef.current = null;
    }
    void key;
  }, []);

  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "k") {
        ev.preventDefault();
        setPaletteOpen((v) => !v);
        setQuery("");
      } else if (ev.key === "Escape") {
        setPaletteOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const commands = useMemo(() => [
    ...[
      ["#top", t.hero.eyebrow.split("·")[0].trim()],
      ["#demo", t.demo.eyebrow],
      ["#capabilities", t.capability.eyebrow],
      ["#how", t.how.eyebrow],
      ["#scenarios", t.scenarios.eyebrow],
      ["#edge", t.edge.eyebrow],
      ["#benchmark", t.bench.eyebrow],
      ["#safety", t.safety.eyebrow],
      ["#privacy", t.privacy.eyebrow],
      ["#faq", t.faq.eyebrow],
    ].map(([href, label]) => ({
      id: href, label, hint: "↵", run: () => { window.location.hash = href; },
    })),
    { id: "lang", label: lang === "vi" ? "Switch to English" : "Chuyển sang Tiếng Việt", hint: "L", run: () => setLang(lang === "vi" ? "en" : "vi") },
    { id: "sound", label: sound ? t.audio.on : t.audio.off, hint: "S", run: () => setSound((v) => !v) },
  ], [t, lang, sound, setLang]);

  const shownCommands = commands.filter((c) =>
    c.label.toLowerCase().includes(query.trim().toLowerCase()));

  const navLinks = useMemo(
    () => [
      { href: "#capabilities", label: t.nav.product },
      { href: "#how", label: t.nav.how },
      { href: "#benchmark", label: t.nav.benchmark },
      { href: "#safety", label: t.nav.safety },
    ],
    [t],
  );

  const alert = scene?.alert ?? null;
  const severity = alert?.severity ?? "silent";
  const activeCond = BENCH_CONDITIONS.find((c) => c.id === cond) ?? BENCH_CONDITIONS[0];
  const activeScn = t.scenarios.tabs[scnTab];

  const candidate = scene?.candidate ?? null;
  const gates = scene?.gates ?? GATE_ORDER.map((id) => ({ id, pass: true, detail: "—" }));
  const outcome = scene?.outcome ?? "idle";
  const reason = scene?.reason ?? null;

  return (
    <div className="rw-landing" ref={revealRef}>
      {/* ============ NAVBAR ============ */}
      <header className={`rw-nav${stuck ? " rw-nav-stuck" : ""}`}>
        <div className="rw-progress" aria-hidden="true"><span style={{ width: `${progress}%` }} /></div>
        <div className="rw-shell">
          <div className="rw-nav-inner">
            <a href="#top" aria-label="RoadWatch"><Logo /></a>
            <nav className="rw-nav-links">
              {navLinks.map((l) => <a key={l.href} href={l.href}>{l.label}</a>)}
            </nav>
            <div className="rw-nav-right">
              <div className="rw-lang" role="group" aria-label="Language">
                {LANGS.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    aria-pressed={lang === l.id}
                    aria-label={l.full}
                    onClick={() => setLang(l.id)}
                  >{l.label}</button>
                ))}
              </div>
              <button
                type="button"
                className="rw-kbd-btn"
                onClick={() => { setPaletteOpen(true); setQuery(""); }}
                aria-label="Command palette"
              ><kbd>⌘</kbd><kbd>K</kbd></button>
              <a className="rw-btn rw-btn-primary" href={demoHref}>{t.nav.cta}</a>
              <button
                type="button"
                className="rw-nav-burger"
                aria-label={t.nav.menu}
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((v) => !v)}
              ><i /></button>
            </div>
          </div>
          {menuOpen ? (
            <nav className="rw-nav-drawer">
              {navLinks.map((l) => (
                <a key={l.href} href={l.href} onClick={() => setMenuOpen(false)}>{l.label}</a>
              ))}
            </nav>
          ) : null}
        </div>
      </header>

      {/* ============ HERO ============ */}
      <section className="rw-dark rw-hero" id="top">
        <div className="rw-shell rw-hero-grid">
          <div className="rw-hero-copy rw-reveal">
            <span className="rw-eyebrow">{t.hero.eyebrow}</span>
            <h1>{t.hero.h1a}<br /><em>{t.hero.h1b}</em></h1>
            <p className="rw-hero-lede">{t.hero.lede}</p>
            <div className="rw-hero-cta">
              <a className="rw-btn rw-btn-primary" href="#demo">
                {t.hero.ctaPrimary}<span className="rw-btn-arrow">→</span>
              </a>
              <a className="rw-btn rw-btn-ghost" href="#benchmark">{t.hero.ctaSecondary}</a>
            </div>
            <div className="rw-badges">
              {t.hero.badges.map((b) => <span className="rw-badge" key={b}>{b}</span>)}
            </div>
          </div>

          <div className="rw-scene rw-reveal">
            <div className="rw-scene-bar">
              <i className="rw-rec" aria-hidden="true" />
              <span>{t.hero.sceneLabel}</span>
              <span className="rw-spacer" />
              <span>1920×1080 · 30 FPS</span>
            </div>
            <DashcamScene scenario="day" playing startAt={6.3} streamUrl={streamUrl} />
            <p className="rw-scene-note">{t.hero.sceneDisclaimer}</p>
          </div>
        </div>
      </section>

      {/* ============ TRUST BAR ============ */}
      <section className="rw-trust">
        <div className="rw-shell rw-trust-inner">
          <span className="rw-trust-label">{t.trust.label}</span>
          <div className="rw-trust-items">
            {t.trust.items.map((i) => (
              <div className="rw-trust-item" key={i.label}>
                <b className="rw-mono">{i.value}</b><span>{i.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ LIVE DEMO ============ */}
      <section className="rw-dark rw-section" id="demo">
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.demo.eyebrow}</span>
            <h2>{t.demo.title}</h2>
            <p>{t.demo.lede}</p>
          </div>

          <div className="rw-demo-controls rw-reveal">
            <div className="rw-tabs" role="group" aria-label={t.demo.eyebrow}>
              {t.demo.scenarios.map((sc) => (
                <button
                  key={sc.id}
                  type="button"
                  aria-pressed={scenario === sc.id}
                  onClick={() => setScenario(sc.id as Scenario)}
                >{sc.label}</button>
              ))}
            </div>
            <button
              type="button"
              className={`rw-play${playing ? "" : " rw-paused"}`}
              onClick={() => { setPlaying((v) => !v); if (!playing) setSeek(null); }}
            >
              <i aria-hidden="true" />{playing ? t.demo.pause : t.demo.play}
            </button>
            <button
              type="button"
              className={`rw-sound${sound ? " rw-sound-on" : ""}`}
              aria-pressed={sound}
              onClick={() => setSound((v) => !v)}
            >
              <span aria-hidden="true">{sound ? "◼◼◼" : "◼◻◻"}</span>
              {sound ? t.audio.on : t.audio.off}
            </button>
          </div>

          <div className="rw-demo-grid rw-reveal">
            <div>
              <div className="rw-scene">
                <div className="rw-scene-bar">
                  <i className="rw-rec" aria-hidden="true" />
                  <span>{playing ? t.demo.playing : t.demo.paused}</span>
                  <span className="rw-spacer" />
                  <span>1920×1080 · 30 FPS</span>
                </div>
                <DashcamScene
                  scenario={scenario}
                  playing={playing}
                  onState={onSceneState}
                  streamUrl={streamUrl}
                  seek={seek}
                />
              </div>

              <div className="rw-scrub">
                <label className="rw-sr" htmlFor="rw-scrub-input">{t.inspector.scrub}</label>
                <div className="rw-scrub-track">
                  <div className="rw-scrub-marks" aria-hidden="true">
                    {TRACE_MARKS.map((m) => (
                      <span
                        key={`${m.id}-${m.at[0]}`}
                        className={`rw-mark rw-mark-${m.outcome}`}
                        style={{ left: `${(m.at[0] / 18) * 100}%`, width: `${((m.at[1] - m.at[0]) / 18) * 100}%` }}
                      />
                    ))}
                  </div>
                  <input
                    id="rw-scrub-input"
                    type="range"
                    min={0}
                    max={18}
                    step={0.1}
                    value={seek ?? scene?.time ?? 0}
                    onChange={(ev) => { setPlaying(false); setSeek(Number(ev.target.value)); }}
                  />
                </div>
                <span className="rw-scrub-time rw-mono">{(seek ?? scene?.time ?? 0).toFixed(1)}s</span>
              </div>

              <div className="rw-chips">
                <span><i />{t.demo.laneDetected}<b>{(scene?.laneQuality ?? 0).toFixed(2)}</b></span>
                <span><i />{t.demo.drivable}<b>{Math.round((scene?.drivable ?? 0) * 100)}%</b></span>
                <span><i />{t.demo.density}<b>{Math.round((scene?.density ?? 0) * 100)}%</b></span>
                <span><i />{t.demo.audioRoute}<b>{t.demo.routeNames[alert?.route ?? "none"]}</b></span>
              </div>
            </div>

            <aside className="rw-readout rw-inspect">
              <div className="rw-readout-head">
                <i className="rw-rec" aria-hidden="true" />{t.inspector.eyebrow}
                <span className="rw-spacer" />
                <span>t = {(scene?.time ?? 0).toFixed(1)}s</span>
              </div>

              <div className="rw-readout-group">
                <div className="rw-readout-title">{t.inspector.candidate}</div>
                {candidate ? (
                  <div className="rw-cand">
                    <span className={`rw-pill rw-pill-${candidate.severity}`}>{t.demo.severity[candidate.severity]}</span>
                    <b className="rw-mono">{candidate.id}</b>
                    <span className="rw-mono">{candidate.track}</span>
                  </div>
                ) : <p className="rw-cand-none">{t.inspector.noCandidate}</p>}
              </div>

              <div className="rw-readout-group">
                <div className="rw-readout-title">{t.inspector.gatesTitle}</div>
                {gates.map((g) => (
                  <div
                    key={g.id}
                    className={`rw-gate ${g.pass ? "rw-gate-ok" : "rw-gate-fail"}`}
                    title={t.inspector.gates[g.id]?.help}
                  >
                    <i aria-hidden="true">{g.pass ? "✓" : "×"}</i>
                    <span>{t.inspector.gates[g.id]?.name ?? g.id}</span>
                    <b className="rw-mono">{g.detail}</b>
                  </div>
                ))}
              </div>

              <div className="rw-readout-group">
                <div className="rw-readout-title">{t.inspector.tracksTitle}</div>
                <table className="rw-tracktable">
                  <thead>
                    <tr>
                      <th scope="col">{t.inspector.cols.track}</th>
                      <th scope="col">{t.inspector.cols.conf}</th>
                      <th scope="col">{t.inspector.cols.hits}</th>
                      <th scope="col">{t.inspector.cols.ego}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(scene?.tracks ?? []).map((r) => (
                      <tr key={r.key}>
                        <td>
                          <i style={{ background: CLASS_DOT[r.kind] ?? "#64748B" }} />
                          {t.demo.classNames[r.kind] ?? r.kind} #{r.track}
                        </td>
                        <td className="rw-mono">{r.conf.toFixed(2)}</td>
                        <td className="rw-mono">{r.hits >= 99 ? "99+" : r.hits}</td>
                        <td className={r.inEgo ? "rw-yes" : "rw-no"}>{r.inEgo ? t.inspector.yes : t.inspector.no}</td>
                      </tr>
                    ))}
                    {(scene?.tracks ?? []).length === 0 ? (
                      <tr><td colSpan={4} className="rw-cand-none">—</td></tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className={`rw-outcome rw-outcome-${outcome}`}>
                <div className="rw-readout-title">{t.inspector.outcomeTitle}</div>
                <div className="rw-outcome-head">
                  <span className={`rw-pill rw-pill-${outcome === "spoken" ? severity : outcome === "hud" ? "advisory" : "silent"}`}>
                    {t.inspector.outcomes[outcome]}
                  </span>
                </div>
                {alert ? <p className="rw-alert-msg">{lang === "vi" ? alert.vi : alert.en}</p> : null}
                {reason ? <p className="rw-reason">{t.inspector.reasons[reason]}</p> : null}
              </div>
            </aside>
          </div>

          <div className="rw-ledger rw-reveal">
            {([
              ["considered", scene?.ledger.considered ?? 5],
              ["spoken", scene?.ledger.spoken ?? 2],
              ["hud", scene?.ledger.hud ?? 1],
              ["suppressed", scene?.ledger.suppressed ?? 2],
            ] as const).map(([k, v]) => (
              <div className={`rw-ledger-tile rw-ledger-${k}`} key={k}>
                <span>{t.inspector.ledger[k]}</span>
                <b className="rw-mono">{v}</b>
              </div>
            ))}
            <p className="rw-ledger-note">{t.inspector.ledger.note}</p>
          </div>

          <p className="rw-demo-foot rw-reveal">{t.audio.note} {t.demo.note}</p>
        </div>
      </section>

      {/* ============ CAPABILITIES ============ */}
      <section className="rw-section" id="capabilities">
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.capability.eyebrow}</span>
            <h2>{t.capability.title}</h2>
            <p>{t.capability.lede}</p>
          </div>
          <div className="rw-cap-grid">
            {t.capability.cards.map((c) => (
              <article className="rw-card rw-reveal" key={c.title}>
                <span className="rw-card-tag">{c.tag}</span>
                <h3>{c.title}</h3>
                <p>{c.body}</p>
                <div className="rw-chiplist">
                  {c.items.map((i) => <span key={i}>{i}</span>)}
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ============ HOW IT WORKS ============ */}
      <section className="rw-section" id="how" style={{ paddingTop: 0 }}>
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.how.eyebrow}</span>
            <h2>{t.how.title}</h2>
          </div>
          <div className="rw-steps rw-reveal">
            {t.how.steps.map((s, i) => (
              <div className="rw-step" key={s.step}>
                <div className="rw-step-idx"><b>{String(i + 1).padStart(2, "0")}</b>{s.step}</div>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            ))}
          </div>
          <div className="rw-highlight rw-reveal">
            <b>EDGE-FIRST</b>
            <p>{t.how.highlight}</p>
          </div>
          <div className="rw-reveal">
            <h3 className="rw-figure-title">{t.pipeline.title}</h3>
            <PipelineDiagram t={t} />
          </div>
        </div>
      </section>

      {/* ============ ALERT SCENARIOS ============ */}
      <section className="rw-section" id="scenarios" style={{ paddingTop: 0 }}>
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.scenarios.eyebrow}</span>
            <h2>{t.scenarios.title}</h2>
            <p>{t.scenarios.lede}</p>
          </div>
          <div className="rw-scn-tabs rw-reveal" role="tablist">
            {t.scenarios.tabs.map((s, i) => (
              <button
                key={s.id}
                type="button"
                role="tab"
                id={`rw-tab-${s.id}`}
                aria-selected={scnTab === i}
                aria-controls={`rw-panel-${s.id}`}
                onClick={() => setScnTab(i)}
              >{s.tab}</button>
            ))}
          </div>
          <div
            className="rw-scn-body rw-reveal"
            role="tabpanel"
            id={`rw-panel-${activeScn.id}`}
            aria-labelledby={`rw-tab-${activeScn.id}`}
          >
            <div className="rw-scn-copy">
              <h3>{activeScn.title}</h3>
              <p>{activeScn.body}</p>
              <div className="rw-voice">
                <small>Voice output</small>
                {activeScn.voice}
              </div>
            </div>
            <dl className="rw-scn-spec">
              <div className="rw-spec-row">
                <dt>{t.scenarios.labels.trigger}</dt>
                <dd>{activeScn.trigger}</dd>
              </div>
              <div className="rw-spec-row">
                <dt>{t.scenarios.labels.level}</dt>
                <dd><span className={`rw-tone rw-tone-${activeScn.levelTone}`}><i />{activeScn.level}</span></dd>
              </div>
              <div className="rw-spec-row">
                <dt>{t.scenarios.labels.output}</dt>
                <dd>{activeScn.output}</dd>
              </div>
              <div className="rw-spec-row">
                <dt>{t.scenarios.labels.control}</dt>
                <dd><span className="rw-none">{t.scenarios.labels.none}</span></dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      {/* ============ EDGE ============ */}
      <section className="rw-dark rw-section" id="edge">
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.edge.eyebrow}</span>
            <h2>{t.edge.title}</h2>
            <p>{t.edge.lede}</p>
          </div>
          <div className="rw-edge-grid">
            <div className="rw-edge-cards rw-reveal">
              {t.edge.cards.map((c) => (
                <article className="rw-edge-card" key={c.title}>
                  <h3>{c.title}</h3>
                  <p>{c.body}</p>
                </article>
              ))}
            </div>
            <div className="rw-spectable rw-reveal">
              <div className="rw-scrollx">
                <table>
                  <caption>{t.edge.tableTitle}</caption>
                  <thead>
                    <tr>{t.edge.tableHead.map((h) => <th key={h} scope="col">{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {SPEC_ROWS.map(([name, value, state]) => (
                      <tr key={name}>
                        <td>{name}</td>
                        <td className="rw-mono">{value}</td>
                        <td>
                          <span className={`rw-state rw-state-${state.toLowerCase().startsWith("active") ? "active" : state.toLowerCase().startsWith("candidate") ? "candidate" : "planned"}`}>
                            {state}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ BENCHMARK ============ */}
      <section className="rw-section" id="benchmark">
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.bench.eyebrow}</span>
            <h2>{t.bench.title}</h2>
            <p>{t.bench.lede}</p>
          </div>

          <div className="rw-bench-grid">
            <div className="rw-panel rw-reveal">
              <div className="rw-panel-head">
                <h3>{t.bench.conditions}</h3>
                <div className="rw-filter" role="group" aria-label={t.bench.conditions}>
                  {BENCH_CONDITIONS.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      aria-pressed={cond === c.id}
                      onClick={() => setCond(c.id)}
                    >{t.bench.conditionLabels[c.id]}</button>
                  ))}
                </div>
              </div>

              {activeCond.status === "measured" ? (
                <>
                  <div className="rw-metrics">
                    <div className="rw-metric">
                      <span>{t.bench.metrics.processed}</span>
                      <b>{activeCond.fps?.toFixed(2)}</b>
                    </div>
                    <div className="rw-metric">
                      <span>{t.bench.metrics.display}</span>
                      <b>{EVIDENCE.runtime.displayFps.toFixed(2)}</b>
                    </div>
                    <div className="rw-metric">
                      <span>{t.bench.metrics.p50}</span>
                      <b>{activeCond.p50?.toFixed(2)}<small>ms</small></b>
                    </div>
                    <div className="rw-metric">
                      <span>{t.bench.metrics.p95}</span>
                      <b>{activeCond.p95?.toFixed(2)}<small>ms</small></b>
                    </div>
                    <div className="rw-metric">
                      <span>{t.bench.metrics.warmup}</span>
                      <b>{(EVIDENCE.runtime.warmupMs / 1000).toFixed(2)}<small>s</small></b>
                    </div>
                    <div className="rw-metric">
                      <span>{t.bench.metrics.errors}</span>
                      <b>{activeCond.errors}</b>
                    </div>
                  </div>
                  <div className="rw-bench-cond">
                    <span>{EVIDENCE.runtime.hardware}</span>
                    <span>{EVIDENCE.runtime.clip} · {EVIDENCE.runtime.provider} · {EVIDENCE.runtime.note}</span>
                    <span>{EVIDENCE.runtime.date}</span>
                  </div>
                </>
              ) : (
                <div className="rw-empty">
                  <strong>{t.bench.noGt}</strong>
                  <p>{t.bench.noGtNote}</p>
                </div>
              )}
            </div>

            <div className="rw-panel rw-reveal">
              <div className="rw-panel-head"><h3>{t.bench.gate}</h3></div>
              <div className="rw-gate">
                <div className="rw-gate-row">
                  <header>
                    <span>{t.bench.metrics.processed}</span>
                    <b>{EVIDENCE.runtime.processedFps.toFixed(2)} / {EVIDENCE.gates.fps}</b>
                  </header>
                  <div className="rw-track">
                    <span className="rw-near" style={{ width: `${Math.min(100, (EVIDENCE.runtime.processedFps / EVIDENCE.gates.fps) * 100)}%` }} />
                  </div>
                </div>
                <div className="rw-gate-row">
                  <header>
                    <span>{t.bench.metrics.p95}</span>
                    <b>{EVIDENCE.runtime.p95.toFixed(2)} / {EVIDENCE.gates.p95} ms</b>
                  </header>
                  <div className="rw-track">
                    <span className="rw-ok" style={{ width: `${Math.min(100, (EVIDENCE.runtime.p95 / EVIDENCE.gates.p95) * 100)}%` }} />
                  </div>
                </div>
                <p style={{ fontSize: 13, color: "var(--rw-muted)" }}>{t.bench.gateNote}</p>
              </div>

            </div>
          </div>

          <div className="rw-panel rw-reveal" style={{ marginTop: 22 }}>
            <div className="rw-panel-head"><h3>{t.chart.title}</h3></div>
            <div className="rw-chartwrap">
              <p className="rw-chart-sub">{t.chart.sub}</p>
              <LatencyChart t={t} />
            </div>
          </div>

          <div className="rw-panel rw-reveal" style={{ marginTop: 22 }}>
            <div className="rw-panel-head"><h3>{t.bench.modelTitle}</h3></div>
            <div className="rw-scrollx">
              <table className="rw-modeltable">
                <tbody>
                  {t.bench.modelRows.map((r) => (
                    <tr key={r.name}>
                      <td>{r.name}</td>
                      <th scope="row" style={{ fontWeight: 500 }}>{r.metric}</th>
                      <td className="rw-num">{r.value}</td>
                      <td><span className={`rw-tag rw-tag-${r.tone}`}>{r.state}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <p className="rw-footnote rw-reveal">{t.bench.footnote}</p>
        </div>
      </section>

      {/* ============ SAFETY BOUNDARY ============ */}
      <section className="rw-dark rw-section" id="safety">
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.safety.eyebrow}</span>
            <h2>{t.safety.title}</h2>
            <p>{t.safety.lede}</p>
          </div>
          <div className="rw-safety-grid rw-reveal">
            <div className="rw-list rw-list-no">
              <h3>{t.safety.notsTitle}</h3>
              <ul>{t.safety.nots.map((n) => <li key={n}>{n}</li>)}</ul>
            </div>
            <div className="rw-list rw-list-yes">
              <h3>{t.safety.dosTitle}</h3>
              <ul>{t.safety.dos.map((n) => <li key={n}>{n}</li>)}</ul>
            </div>
          </div>
          <p className="rw-safety-foot rw-reveal">{t.safety.footer}</p>
        </div>
      </section>

      {/* ============ PRIVACY ============ */}
      <section className="rw-section" id="privacy">
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.privacy.eyebrow}</span>
            <h2>{t.privacy.title}</h2>
            <p>{t.privacy.lede}</p>
          </div>
          <div className="rw-priv-grid">
            {t.privacy.items.map((p, i) => (
              <article className="rw-priv rw-reveal" key={p.title}>
                <span className="rw-priv-num">{String(i + 1).padStart(2, "0")}</span>
                <h3>{p.title}</h3>
                <p>{p.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ============ FAQ ============ */}
      <section className="rw-section" id="faq" style={{ paddingTop: 0 }}>
        <div className="rw-shell">
          <div className="rw-head rw-reveal">
            <span className="rw-eyebrow">{t.faq.eyebrow}</span>
            <h2>{t.faq.title}</h2>
          </div>
          <div className="rw-faq rw-reveal">
            {t.faq.items.map((f) => (
              <details key={f.q}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ============ FINAL CTA + FOOTER ============ */}
      <section className="rw-dark rw-section" id="cta" style={{ paddingBottom: 0 }}>
        <div className="rw-shell">
          <div className="rw-cta-inner rw-reveal">
          <span className="rw-eyebrow">ROADWATCH COPILOT</span>
          <h2>{t.cta.title}</h2>
          <p>{t.cta.lede}</p>
            <div className="rw-cta-row">
              <a className="rw-btn rw-btn-primary" href={demoHref}>{t.cta.primary}<span className="rw-btn-arrow">→</span></a>
              <a className="rw-btn rw-btn-ghost" href="#benchmark">{t.cta.secondary}</a>
              <a className="rw-btn rw-btn-ghost" href="#cta">{t.cta.tertiary}</a>
            </div>
          </div>
        </div>

        <footer className="rw-shell rw-footer">
          <div className="rw-footer-grid">
            <div className="rw-footer-brand">
              <Logo />
              <p>{t.footer.tagline}</p>
            </div>
            {t.footer.cols.map((c) => (
              <div key={c.title}>
                <h4>{c.title}</h4>
                <ul>{c.links.map((l) => <li key={l}><a href="#top">{l}</a></li>)}</ul>
              </div>
            ))}
          </div>
          <div className="rw-footer-bar">
            <span>© {new Date().getFullYear()} RoadWatch Copilot</span>
            <span>{t.footer.legal}</span>
            <span className="rw-guardrail">⚠ {t.footer.guardrail}</span>
          </div>
        </footer>
      </section>

      {paletteOpen ? (
        <div className="rw-palette" role="dialog" aria-modal="true" aria-label="Command palette"
          onClick={(ev) => { if (ev.target === ev.currentTarget) setPaletteOpen(false); }}>
          <div className="rw-palette-box">
            <input
              autoFocus
              className="rw-palette-input"
              placeholder={lang === "vi" ? "Đi tới phần…" : "Jump to…"}
              value={query}
              onChange={(ev) => setQuery(ev.target.value)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter" && shownCommands[0]) {
                  shownCommands[0].run();
                  setPaletteOpen(false);
                }
              }}
            />
            <ul className="rw-palette-list">
              {shownCommands.map((c) => (
                <li key={c.id}>
                  <button type="button" onClick={() => { c.run(); setPaletteOpen(false); }}>
                    <span>{c.label}</span><kbd>{c.hint}</kbd>
                  </button>
                </li>
              ))}
              {shownCommands.length === 0 ? <li className="rw-palette-empty">—</li> : null}
            </ul>
          </div>
        </div>
      ) : null}

      {/* sticky CTA chỉ hiện trên mobile */}
      <div className="rw-sticky-cta">
        <span>{t.footer.guardrail}</span>
        <a className="rw-btn rw-btn-primary" href="#demo">{t.nav.cta}</a>
      </div>
    </div>
  );
}

const CLASS_DOT: Record<string, string> = {
  car: "#38BDF8",
  motorcycle: "#F59E0B",
  pedestrian: "#22C55E",
  truck: "#A78BFA",
};

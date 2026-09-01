import { useEffect, useRef, useState } from "react";

export type Alert = {
  /** null = dòng chỉ hiện trên HUD, không bao giờ ra loa nên không có file */
  slug: string | null;
  event: string;
  line: string;
  channel: string;
  mode: "voice" | "conditional" | "hud";
  danger: boolean;
  seconds: number;
};

const MICRO = "text-[clamp(0.6875rem,0.62vw,0.9rem)]";

/**
 * Danh sách câu cảnh báo, phát bằng file do chính Piper của web_demo sinh ra.
 *
 * Một thẻ <audio> duy nhất dùng lại cho mọi dòng: trình duyệt chỉ phát được
 * một câu tại một thời điểm, mà đó cũng đúng là ràng buộc của kênh loa thật —
 * cổng phát chỉ cho một câu ra loa mỗi lúc.
 */
export default function VoiceList({ alerts }: { alerts: readonly Alert[] }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onEnd = () => { setPlaying(null); setProgress(0); };
    const onTime = () => {
      if (el.duration > 0) setProgress(el.currentTime / el.duration);
    };
    const onError = () => { setFailed(true); onEnd(); };
    el.addEventListener("ended", onEnd);
    el.addEventListener("timeupdate", onTime);
    el.addEventListener("error", onError);
    return () => {
      el.removeEventListener("ended", onEnd);
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("error", onError);
    };
  }, []);

  function toggle(slug: string) {
    const el = audioRef.current;
    if (!el) return;
    if (playing === slug) {
      el.pause();
      setPlaying(null);
      setProgress(0);
      return;
    }
    el.pause();
    el.src = `/landing/voice/${slug}.mp3`;
    el.currentTime = 0;
    setProgress(0);
    setPlaying(slug);
    // play() bị chặn nếu chưa có cử chỉ người dùng; ở đây luôn có vì hàm này
    // chỉ chạy từ click, nhưng vẫn bắt lỗi để không ném promise chưa xử lý.
    el.play().catch(() => { setFailed(true); setPlaying(null); });
  }

  return (
    <div className="border-t border-border">
      <audio ref={audioRef} preload="none" />
      {alerts.map((a) => {
        const on = a.slug !== null && playing === a.slug;
        return (
          <div
            key={a.event}
            data-reveal
            className="grid grid-cols-1 gap-2 border-b border-border py-[clamp(1rem,1.4vw,1.75rem)] md:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)_minmax(8rem,0.55fr)] md:items-baseline md:gap-x-[clamp(1.5rem,2.6vw,3.5rem)]"
          >
            <div className={`flex items-center gap-3 font-mono ${MICRO} tracking-[0.14em] text-text-low`}>
              <span
                className={
                  "inline-block size-1.5 shrink-0 rounded-full " +
                  (a.danger ? "bg-state-alert" : "bg-signal")
                }
              />
              {a.event.toUpperCase()}
            </div>

            <div>
              {a.slug === null ? (
                // Không có nút phát: dòng này chỉ hiện trên HUD. Chừa đúng
                // khoảng thụt của các dòng có nút để cột chữ vẫn thẳng hàng.
                <div className="flex items-baseline gap-3 text-[clamp(1.0625rem,1.35vw,2rem)] font-light leading-snug text-text-mid">
                  <span aria-hidden className="inline-block size-[1.05em] shrink-0" />
                  <span>“{a.line}”</span>
                </div>
              ) : (
              <button
                type="button"
                onClick={() => toggle(a.slug as string)}
                aria-label={`Nghe câu cảnh báo: ${a.line}`}
                className={
                  "group flex w-full items-baseline gap-3 text-left text-[clamp(1.0625rem,1.35vw,2rem)] font-light leading-snug " +
                  "cursor-pointer bg-transparent p-0 " +
                  (a.danger ? "text-state-alert" : "text-foreground")
                }
              >
                <span
                  aria-hidden
                  className={
                    "mt-[0.35em] inline-flex size-[1.05em] shrink-0 items-center justify-center self-start rounded-full border transition-colors " +
                    (on
                      ? a.danger ? "border-state-alert bg-state-alert" : "border-signal bg-signal"
                      : "border-current opacity-45 group-hover:opacity-100")
                  }
                >
                  <svg viewBox="0 0 10 10" className="size-[0.5em]" fill="none">
                    {on ? (
                      <path d="M2 1h2v8H2zM6 1h2v8H6z" fill="var(--surface-0)" />
                    ) : (
                      <path d="M2.5 1.2 8.3 5 2.5 8.8z" fill="currentColor" />
                    )}
                  </svg>
                </span>
                <span>“{a.line}”</span>
              </button>
              )}

              {/* thanh tiến trình chỉ hiện khi câu đang phát */}
              <div className="mt-2 ml-[calc(1.05em+0.75rem)] h-px bg-border" hidden={!on}>
                <div
                  className={"h-px " + (a.danger ? "bg-state-alert" : "bg-signal")}
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
            </div>

            <div
              className={
                `font-mono ${MICRO} tracking-[0.12em] ` +
                (a.mode === "voice"
                  ? "text-signal"
                  : a.mode === "conditional"
                    ? "text-text-mid"
                    : "text-text-low")
              }
            >
              {a.channel}
              {a.slug !== null && (
                <span className="ml-2 text-text-low">{a.seconds.toFixed(2)}s</span>
              )}
            </div>
          </div>
        );
      })}
      {failed && (
        <p className={`mt-4 font-mono ${MICRO} text-state-alert`}>
          Không phát được file âm thanh. Kiểm tra thư mục /landing/voice trong bản build.
        </p>
      )}
    </div>
  );
}

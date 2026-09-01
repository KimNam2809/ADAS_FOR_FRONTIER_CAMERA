import { useEffect, useState } from "react";

/**
 * Nút bật/tắt toàn màn hình.
 *
 * Trình duyệt bắt buộc requestFullscreen() phải xuất phát từ một thao tác của
 * người dùng, nên không thể tự bật lúc tải trang. Trong iframe không có
 * allow="fullscreen" (ví dụ pane xem của IDE) lời gọi sẽ bị từ chối — khi đó
 * nút tự ẩn đi thay vì đứng im không phản hồi.
 */
/** Bật/tắt fullscreen trên phần tử gốc. Ném lỗi nếu môi trường không cho. */
function toggleFullscreen(): Promise<void> {
  return document.fullscreenElement
    ? document.exitFullscreen()
    : (document.documentElement.requestFullscreen?.() ?? Promise.reject(new Error("unsupported")));
}

export default function FullscreenToggle() {
  const [on, setOn] = useState(false);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    const sync = () => setOn(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", sync);
    setAvailable(Boolean(document.fullscreenEnabled));

    // Phím tắt F — cũng là một thao tác người dùng nên trình duyệt chấp nhận.
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "f" && e.key !== "F") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const el = document.activeElement;
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return;
      e.preventDefault();
      void toggleFullscreen();
    };
    window.addEventListener("keydown", onKey);

    return () => {
      document.removeEventListener("fullscreenchange", sync);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  if (!available) return null;

  const toggle = () => void toggleFullscreen().catch(() => setAvailable(false));

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={on ? "Thoát toàn màn hình" : "Xem toàn màn hình"}
      title={on ? "Thoát toàn màn hình (F)" : "Xem toàn màn hình (F)"}
      className="absolute top-[clamp(1.5rem,2.4vw,3rem)] right-[clamp(1.5rem,3.2vw,5.5rem)] z-10 grid size-9 place-items-center rounded-sm text-text-mid transition-colors hover:text-signal"
    >
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="square">
        {on ? (
          <>
            <path d="M9 3v6H3M15 3v6h6M9 21v-6H3M15 21v-6h6" />
          </>
        ) : (
          <>
            <path d="M3 9V3h6M21 9V3h-6M3 15v6h6M21 15v6h-6" />
          </>
        )}
      </svg>
    </button>
  );
}

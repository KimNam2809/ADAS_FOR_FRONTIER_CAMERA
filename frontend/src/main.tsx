import React from "react";
import { createRoot } from "react-dom/client";

const root = createRoot(document.getElementById("root")!);
const dashboardRoute = /^\/app(?:\/|$)/.test(window.location.pathname);

function setMetadata(title: string, description: string, themeColor: string) {
  document.title = title;
  document.querySelector<HTMLMetaElement>('meta[name="description"]')?.setAttribute("content", description);
  document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')?.setAttribute("content", themeColor);
}

async function bootstrap() {
  if (dashboardRoute) {
    const [{ default: RoadWatchApp }] = await Promise.all([
      import("./RoadWatchApp"),
      import("./styles.css"),
    ]);
    setMetadata(
      "RoadWatch Copilot — Dashboard kỹ thuật",
      "Driver HUD và Engineer Dashboard của RoadWatch Copilot.",
      "#0868ff",
    );
    root.render(<React.StrictMode><RoadWatchApp /></React.StrictMode>);
    return;
  }

  const [{ default: LandingPage }] = await Promise.all([
    import("./landing/App"),
    import("./landing/index.css"),
  ]);
  setMetadata(
    "RoadWatch Copilot — Cảnh báo ADAS tiếng Việt tại edge",
    "RoadWatch Copilot là trợ lý cảnh báo ADAS warning-only, chạy edge và phát cảnh báo giọng nói tiếng Việt ngoại tuyến.",
    "#f8f9fb",
  );
  root.render(<React.StrictMode><LandingPage /></React.StrictMode>);
}

void bootstrap();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register("/sw.js").catch(() => undefined);
}

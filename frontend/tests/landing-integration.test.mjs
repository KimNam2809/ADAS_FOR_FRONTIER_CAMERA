import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFileSync(resolve(frontend, path), "utf8");

test("root and /app load isolated React bundles", () => {
  const entry = read("src/main.tsx");
  const dashboard = read("src/RoadWatchApp.tsx");

  assert.match(entry, /\/\^\\\/app\(\?:\\\/\|\$\)\//);
  assert.match(entry, /import\("\.\/landing\/App"\)/);
  assert.match(entry, /import\("\.\/landing\/index\.css"\)/);
  assert.match(entry, /import\("\.\/RoadWatchApp"\)/);
  assert.match(entry, /import\("\.\/styles\.css"\)/);
  assert.doesNotMatch(dashboard, /createRoot/);
  assert.match(dashboard, /export default function RoadWatchApp/);
  assert.match(dashboard, /href="\/"/);
  assert.match(dashboard, /Quay lại landing page RoadWatch/);
});

test("landing CTA opens the integrated dashboard", () => {
  const app = read("src/landing/App.tsx");
  assert.match(app, /CONFIGURED_DEMO_URL \|\| "\/app\/"/);
  assert.match(app, /Mở bảng điều khiển trực tiếp/);
  assert.match(app, /Chỉ hỗ trợ cảnh báo — không tự lái/);
  assert.match(app, /src="\/logo\.png"/);
  assert.ok(existsSync(resolve(frontend, "public/logo.png")), "RoadWatch logo must be packaged");
});

test("landing assets are namespaced and packaged", () => {
  const required = [
    "public/landing/favicon.svg",
    "public/landing/evidence/camera-mount.jpg",
    "public/landing/evidence/jetson-orin.jpg",
    "public/landing/evidence/tv3-shipping-wide.jpg",
    "public/landing/voice/fcw.mp3",
    "public/landing/voice/manifest.json",
    "public/landing/3d/corridor.html",
    "public/landing/3d/corridor.js",
    "public/landing/3d/vendor/three/three.module.js",
    "public/landing/3d/vendor/three/LICENSE",
  ];
  for (const path of required) {
    assert.ok(existsSync(resolve(frontend, path)), `${path} must be packaged`);
  }

  const app = read("src/landing/App.tsx");
  const voice = read("src/landing/components/VoiceList.tsx");
  assert.doesNotMatch(app, /["']\/evidence\//);
  assert.doesNotMatch(app, /["']\/3d\//);
  assert.match(app, /\/landing\/3d\/corridor\.html/);
  assert.match(voice, /\/landing\/voice\/\$\{slug\}\.mp3/);
});

test("3D viewer stays self-contained for offline deployment", () => {
  const corridor = read("public/landing/3d/corridor.js");
  const stage = read("public/landing/3d/three-d-stage.js");
  const theme = read("public/landing/3d/_ds/nocturne-645cc0b2-ab3b-4760-8331-46bdf9c14ecf/styles.css");
  assert.match(corridor, /from '\.\/vendor\/three\/three\.module\.js'/);
  assert.match(stage, /shadowMap\.type = THREE\.PCFShadowMap/);
  assert.doesNotMatch(stage, /shadowMap\.type = THREE\.PCFSoftShadowMap/);
  assert.doesNotMatch(theme, /@import\s+url\(['"]https?:\/\//);
});

test("hero captions use tweenable objects instead of numeric array properties", () => {
  const hero = read("src/landing/components/AdasHero.tsx");
  const scene = read("src/landing/lib/heroScene.ts");
  assert.match(scene, /captions: Array<\{ alpha: number \}>/);
  assert.match(hero, /state\.captions\[i\], \{ alpha: 1/);
  assert.doesNotMatch(hero, /tl\.(?:set|to)\(state\.captions, \{ [0-9]/);
});

test("landing bundles a Vietnamese-capable font at every used text weight", () => {
  const css = read("src/landing/index.css");
  for (const weight of [300, 400, 500, 700]) {
    assert.match(css, new RegExp(`@fontsource/be-vietnam-pro/${weight}\\.css`));
  }
  assert.match(css, /--font-sans: "Be Vietnam Pro"/);
  assert.ok(
    existsSync(resolve(frontend, "node_modules/@fontsource/be-vietnam-pro/LICENSE")),
    "Be Vietnam Pro package and OFL license must be installed",
  );
});

test("service worker caches both public entry points", () => {
  const worker = read("public/sw.js");
  assert.match(worker, /roadwatch-shell-v4/);
  assert.match(worker, /"\/app\/"/);
  assert.match(worker, /"\/landing\/favicon\.svg"/);
});

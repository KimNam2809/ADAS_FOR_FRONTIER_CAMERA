// Tách khỏi <script type="module"> inline trong corridor.html.
// CSP của trang là `script-src 'self'` — không có 'unsafe-inline' — nên mọi
// script inline đều bị chặn, kể cả <script type="importmap">. Vì vậy file này
// import three bằng ĐƯỜNG DẪN TƯƠNG ĐỐI, không dùng bare specifier 'three',
// và không cần import map nào cả.
import * as THREE from './vendor/three/three.module.js';
import {
  CAM, F_PX, zOf, makeMaterials, sedan, lightTruck, pedestrian, motorbike, speedSign,
  frustum, groundStrip, bracketBox, contourArc, ray, straightRoad, countTriangles
} from './roadwatch-parts.js';

const stage = document.querySelector('three-d-stage');
await stage.ready;

// Thanh tải OBJ/GLB nằm trong shadow DOM và không có `part`, nên ::part() không
// với tới. Ẩn trực tiếp: người xem landing không cần export tài sản 3D.
stage.shadowRoot?.querySelector('.toolbar')?.style.setProperty('display', 'none');

const M = makeMaterials();
const model = new THREE.Group();
model.name = 'RW_A01_CORRIDOR';
const D = (d) => zOf(d);

// ── Reference empties (xuất kèm GLB, không xuất camera object) ───────────
const empty = (name, pos) => { const o = new THREE.Object3D(); o.name = name; o.position.set(...pos); model.add(o); return o; };
empty('RW_REF_CAMERA_ORIGIN', [CAM.x, CAM.y, CAM.z]).rotation.x = CAM.pitch * Math.PI / 180;
empty('RW_A01_CAM_DASHCAM', [0, 1.32, -1.75]);
empty('RW_A01_CAM_TOPDOWN', [-1.6, 34.0, -20.0]);
empty('RW_A01_CAM_ORBIT_HOME', [14.5, 9.0, 6.0]);

// ── Environment ─────────────────────────────────────────────────────────
model.add(straightRoad(M));

// ── Ego ─────────────────────────────────────────────────────────────────
const ego = sedan(M, 'RW_A01_EGO', M.MAT_EGO);
ego.name = 'RW_A01_EGO_BODY';
model.add(ego);

// ── Actors (d đo từ gốc camera dọc theo −Z) ──────────────────────────────
const actors = new THREE.Group(); actors.name = 'RW_A01_ACTORS'; model.add(actors);

const lead = sedan(M, 'RW_A01_ACT_VEH_LEAD');
lead.position.set(0.15, 0, D(18.0));
actors.add(lead);

const truck = lightTruck(M, 'RW_A01_ACT_VEH_TRUCK');
truck.position.set(-3.50, 0, D(26.0));
actors.add(truck);

const moto = motorbike(M, 'RW_A01_ACT_MOTO_CUTIN');
moto.position.set(1.20, 0, D(11.5));
moto.rotation.y = 12 * Math.PI / 180;   // đang tạt vào hành lang
actors.add(moto);

const pedCross = pedestrian(M, 'RW_A01_ACT_PED_CROSSING', { stride: 0.34 });
pedCross.position.set(-3.90, 0, D(11.0));
pedCross.rotation.y = -Math.PI / 2;      // đi về +X, trong lòng đường
actors.add(pedCross);

const pedWalk = pedestrian(M, 'RW_A01_ACT_PED_SIDEWALK', { stride: 0.16 });
pedWalk.position.set(-6.20, 0.14, D(13.0));
pedWalk.rotation.y = 0.5;
actors.add(pedWalk);

const sign = speedSign(M, 'RW_A01_ACT_SIGN_SPEED');
sign.position.set(3.00, 0.14, D(24.0));
sign.rotation.y = Math.PI;               // mặt biển hướng về xe ego
actors.add(sign);

// ── Inference layer ─────────────────────────────────────────────────────
const inf = new THREE.Group(); inf.name = 'RW_A01_INF'; model.add(inf);
inf.add(frustum(M, 'RW_A01_INF_FRUSTUM'));
inf.add(groundStrip(M, 'RW_A01_INF_CORRIDOR', { xCenter: 0, wNear: 2.6, wFar: 3.4, dNear: 0, dFar: 45, y: 0.020 }));
const drivable = groundStrip(M, 'RW_A01_INF_DRIVABLE', { xCenter: -1.70, wNear: 7.10, wFar: 7.10, dNear: -3, dFar: 58, y: 0.012 });
drivable.material = M.MAT_INFER.clone();
drivable.material.name = 'MAT_INFER';
drivable.material.opacity = 0.10;
inf.add(drivable);

const boxes = new THREE.Group(); boxes.name = 'RW_A01_INF_BOXES'; inf.add(boxes);
const boxSpec = [
  ['LEAD', lead.position, { w: 1.86, h: 1.48, l: 4.64 }, 0, 0, -1.30],
  ['TRUCK', truck.position, { w: 2.26, h: 2.60, l: 5.94 }, 0, 0, -1.35],
  ['MOTO_CUTIN', moto.position, { w: 0.86, h: 1.76, l: 2.00 }, 12],
  ['PED_CROSSING', pedCross.position, { w: 0.70, h: 1.76, l: 0.56 }],
  ['PED_SIDEWALK', pedWalk.position, { w: 0.70, h: 1.76, l: 0.56 }, 0, 0.14],
  ['SIGN_SPEED', sign.position, { w: 0.72, h: 0.76, l: 0.14 }, 0, 1.96]
];
for (const [key, pos, dims, yawDeg = 0, yLift = 0, zOff = 0] of boxSpec) {
  const b = bracketBox(M, `RW_A01_INF_BOX_${key}`, dims);
  b.position.set(pos.x, b.position.y + yLift, pos.z + zOff);
  b.rotation.y = yawDeg * Math.PI / 180;
  boxes.add(b);
}

// ── Asset 02 — nêm bất định ─────────────────────────────────────────────
const A02 = new THREE.Group(); A02.name = 'RW_A02_WEDGE'; A02.visible = false; model.add(A02);
const H_BOX = 96, W_BOX = 52;              // px, trên ảnh 1920 × 1080
const D_MIN = F_PX * 1.45 / H_BOX;         // 25.1 m
const D_MAX = F_PX * 1.95 / H_BOX;         // 33.8 m
const D_CAL = 29.4, CAL_T = 2.4;
const wAt = (d) => W_BOX * d / F_PX;
const X_T = 0.10;

const target = pedestrian(M, 'RW_A02_TARGET_PED');
target.position.set(X_T, 0, D(D_CAL));
target.rotation.y = Math.PI;
A02.add(target);

const raw = groundStrip(M, 'RW_A02_WEDGE_RAW', {
  xCenter: X_T, wNear: wAt(D_MIN), wFar: wAt(D_MAX), dNear: D_MIN, dFar: D_MAX, y: 0.030
});
A02.add(raw);

const cal = groundStrip(M, 'RW_A02_WEDGE_CAL', {
  xCenter: X_T, wNear: wAt(D_CAL - CAL_T / 2), wFar: wAt(D_CAL + CAL_T / 2),
  dNear: D_CAL - CAL_T / 2, dFar: D_CAL + CAL_T / 2, y: 0.042, mat: M.MAT_ALERT
});
cal.visible = false;
A02.add(cal);

const rays = new THREE.Group(); rays.name = 'RW_A02_RAYS'; A02.add(rays);
[[-1, 0], [1, 0], [1, 1], [-1, 1]].forEach(([sx, sy], i) => {
  const corner = new THREE.Vector3(X_T + sx * wAt(D_CAL) / 2, sy * 1.72, D(D_CAL));
  const from = new THREE.Vector3(CAM.x, CAM.y, CAM.z);
  const dir = corner.clone().sub(from);
  const t = (40 - 0) / (D_CAL);           // kéo dài tới 40 m
  rays.add(ray(M, `RW_A02_RAYS_${i}`, from.clone().add(dir.multiplyScalar(t)).toArray()));
});

[10, 20, 30].forEach(R => A02.add(contourArc(M, `RW_A02_CONTOUR_${R}`, R)));

// ── Mount ───────────────────────────────────────────────────────────────
stage.setObject(model);
// setObject bật shadow cho mọi mesh — lớp suy luận không đổ/nhận bóng.
model.traverse(o => {
  if (o.isMesh && o.material && /MAT_INFER|MAT_ALERT/.test(o.material.name || '')) {
    o.castShadow = false; o.receiveShadow = false;
  }
});
document.getElementById('tris').textContent =
  countTriangles(model).toLocaleString('vi-VN') + ' tam giác · ngân sách 45 000';

// ── Camera presets ──────────────────────────────────────────────────────
const cam = stage._camera, ctr = stage._controls;
ctr.minPolarAngle = 12 * Math.PI / 180;   // cao độ 78°
ctr.maxPolarAngle = 82 * Math.PI / 180;   // cao độ 8°
const PRESETS = {
  dashcam: { p: [0, 1.32, -1.75], t: [0, 1.20, -40], fov: 36.6 },
  topdown: { p: [-1.6, 34.0, -20.0], t: [-1.601, 0, -20.0], fov: 42 },
  orbit: { p: [14.5, 9.0, 6.0], t: [0, 0.8, -16.0], fov: 38 }
};
function goTo(key) {
  const c = PRESETS[key];
  cam.fov = c.fov; cam.near = 0.1; cam.far = 400; cam.updateProjectionMatrix();
  cam.position.set(...c.p);
  ctr.target.set(...c.t);
  ctr.update();
  // Ở góc dashcam, hình nón chính là khung hình này — vẽ nó ra chỉ phủ kín màn.
  const fr = model.getObjectByName('RW_A01_INF_FRUSTUM');
  fr.visible = key !== 'dashcam';
  document.querySelector('[data-layer="RW_A01_INF_FRUSTUM"]').setAttribute('aria-pressed', String(fr.visible));
  document.querySelectorAll('#cams .btn').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.cam === key)));
}
document.getElementById('cams').addEventListener('click', e => {
  const b = e.target.closest('button'); if (b) goTo(b.dataset.cam);
});
goTo('orbit');

// ── Layer toggles ───────────────────────────────────────────────────────
document.getElementById('layers').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const node = model.getObjectByName(b.dataset.layer);
  if (!node) return;
  node.visible = !node.visible;
  b.setAttribute('aria-pressed', String(node.visible));
});

// ── Asset 02 modes ──────────────────────────────────────────────────────
const calcEl = document.getElementById('calc');
const CALC = {
  raw: `<strong>Chiều sâu suy ra từ chiều cao box</strong><br>
    <code>f_px = (1920/2) / tan(30°) = ${F_PX.toFixed(1)} px</code><br>
    <code>d = f_px × H_thật / h_box</code>, h_box = ${H_BOX} px, H_thật ∈ [1.45 m, 1.95 m]<br>
    <code>d ∈ [${D_MIN.toFixed(1)} m , ${D_MAX.toFixed(1)} m]</code> — nêm dài ${(D_MAX - D_MIN).toFixed(1)} m<br>
    <em>Ví dụ tính toán, chưa phải kết quả đo trên xe.</em>`,
  cal: `<strong>Sau hiệu chuẩn — dùng điểm chân chạm đất</strong><br>
    <code>d = h_cam / tan(θ_chúc + atan((y_chân − c_y) / f_px))</code><br>
    <code>d = 29.4 m ± 1.2 m</code> — nêm co lại còn một lát mỏng<br>
    <em>Ví dụ tính toán, chưa phải kết quả đo trên xe.</em>`
};
document.getElementById('wedge').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const mode = b.dataset.wedge;
  A02.visible = mode !== 'off';
  raw.visible = mode === 'raw';
  cal.visible = mode === 'cal';
  calcEl.style.display = mode === 'off' ? 'none' : 'block';
  calcEl.innerHTML = CALC[mode] || '';
  document.querySelectorAll('#wedge .btn').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.wedge === mode)));
});

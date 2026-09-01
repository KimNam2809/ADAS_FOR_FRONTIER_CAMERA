// RoadWatch — shared 3D part library (spec v1.0)
// Units: metres. +Y up, −Z forward, origin at rear-axle centre on the ground.
// Đường dẫn tương đối, không phải bare specifier: trang chạy dưới CSP
// `script-src 'self'` nên không có import map (import map là script inline).
import * as THREE from './vendor/three/three.module.js';

export const CAM = { x: 0, y: 1.32, z: -1.75, pitch: -2.0, fovH: 60, fovV: 36.6, near: 1.5, far: 60 };
export const F_PX = (1920 / 2) / Math.tan((CAM.fovH / 2) * Math.PI / 180); // 1662.8

// distance d is measured from the camera origin along −Z
export const zOf = (d) => CAM.z - d;

// ── Materials — 6 slots for the whole set ────────────────────────────────
export function makeMaterials() {
  const M = {
    MAT_BODY_DARK: new THREE.MeshStandardMaterial({ color: 0x2a3441, roughness: 0.85, metalness: 0 }),
    MAT_BODY_MID: new THREE.MeshStandardMaterial({ color: 0x6b7b8f, roughness: 0.9, metalness: 0 }),
    MAT_GROUND: new THREE.MeshStandardMaterial({ color: 0x3a4250, roughness: 1.0, metalness: 0 }),
    MAT_EGO: new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.6, metalness: 0.1 }),
    MAT_INFER: new THREE.MeshStandardMaterial({
      color: 0x7c3aed, emissive: 0x7c3aed, emissiveIntensity: 0.15,
      transparent: true, opacity: 0.20, side: THREE.DoubleSide, depthWrite: false
    }),
    MAT_ALERT: new THREE.MeshStandardMaterial({
      color: 0xdc2626, emissive: 0xdc2626, emissiveIntensity: 0.25,
      transparent: true, opacity: 0.34, side: THREE.DoubleSide, depthWrite: false
    })
  };
  for (const [name, m] of Object.entries(M)) m.name = name;
  return M;
}

const noShadow = (o) => { o.traverse(n => { n.castShadow = false; n.receiveShadow = false; }); return o; };
const solid = (o) => { o.traverse(n => { if (n.isMesh) { n.castShadow = true; n.receiveShadow = true; } }); return o; };

function mesh(geo, mat, name) { const m = new THREE.Mesh(geo, mat); m.name = name; return m; }

// ── Body shells ──────────────────────────────────────────────────────────
// Side profile given as [u, y] pairs where u = −z (u grows toward the front).
function profileBody(points, width, depthOffsetU = 0) {
  const shape = new THREE.Shape();
  points.forEach(([u, y], i) => i ? shape.lineTo(u, y) : shape.moveTo(u, y));
  shape.closePath();
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth: width, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.03, bevelSegments: 2, steps: 1
  });
  geo.rotateY(Math.PI / 2);          // (u,y,w) → (w, y, −u)
  geo.translate(-width / 2, 0, depthOffsetU);
  return geo;
}

const SEDAN_PROFILE = [
  [-1.00, 0.28], [3.60, 0.28], [3.60, 0.66], [3.35, 0.86], [2.80, 0.92],
  [2.25, 1.40], [0.70, 1.45], [-0.15, 1.06], [-0.94, 0.94], [-1.00, 0.62]
];

function wheel(mats, name, r = 0.33, w = 0.22) {
  const geo = new THREE.CylinderGeometry(r, r, w, 18);
  geo.rotateZ(Math.PI / 2);
  return mesh(geo, mats.MAT_BODY_DARK, name);
}

function wheelSet(mats, prefix, xs, zs, r = 0.33, w = 0.22) {
  const g = new THREE.Group();
  g.name = prefix;
  zs.forEach((z, i) => xs.forEach((x, j) => {
    const m = wheel(mats, `${prefix}_${i}${j}`, r, w);
    m.position.set(x, r, z);
    g.add(m);
  }));
  return g;
}

/** Neutral C-segment sedan: 4.60 × 1.82 × 1.45, no grille, no badge. */
export function sedan(mats, name, bodyMat) {
  const g = new THREE.Group();
  g.name = name;
  g.add(mesh(profileBody(SEDAN_PROFILE, 1.82), bodyMat || mats.MAT_BODY_DARK, `${name}_BODY`));
  // sill skirt gives the silhouette a shadow line
  const sill = mesh(new THREE.BoxGeometry(1.78, 0.16, 4.30), mats.MAT_BODY_DARK, `${name}_SILL`);
  sill.position.set(0, 0.24, -1.30);
  g.add(sill);
  const glass = mesh(profileBody([[2.18, 1.37], [0.74, 1.42], [-0.06, 1.06], [1.86, 1.02]], 1.74), mats.MAT_BODY_MID, `${name}_GLASS`);
  glass.position.y = 0.004;
  g.add(glass);
  g.add(wheelSet(mats, `${name}_WHEELS`, [-0.80, 0.80], [0, -2.70]));
  return solid(g);
}

/** Light truck / box van, 5.90 long. */
export function lightTruck(mats, name) {
  const g = new THREE.Group();
  g.name = name;
  const cab = mesh(profileBody([[2.30, 0.42], [4.30, 0.42], [4.30, 1.85], [4.02, 2.05], [2.30, 2.05]], 2.05), mats.MAT_BODY_MID, `${name}_CAB`);
  g.add(cab);
  const box = mesh(new THREE.BoxGeometry(2.20, 2.10, 3.80), mats.MAT_BODY_MID, `${name}_BOX`);
  box.position.set(0, 1.35, -0.30);
  g.add(box);
  const chassis = mesh(new THREE.BoxGeometry(2.00, 0.28, 5.70), mats.MAT_BODY_DARK, `${name}_CHASSIS`);
  chassis.position.set(0, 0.42, -1.25);
  g.add(chassis);
  g.add(wheelSet(mats, `${name}_WHEELS`, [-0.92, 0.92], [0, -3.10], 0.42, 0.26));
  return solid(g);
}

/** City bus, 9.5 m — the occluder in the diorama. */
export function bus(mats, name) {
  const g = new THREE.Group();
  g.name = name;
  const body = mesh(profileBody([[-2.50, 0.48], [7.00, 0.48], [7.00, 2.90], [6.75, 3.10], [-2.25, 3.10], [-2.50, 2.90]], 2.50), mats.MAT_BODY_MID, `${name}_BODY`);
  g.add(body);
  const band = mesh(profileBody([[-2.40, 1.75], [6.90, 1.75], [6.90, 2.60], [-2.40, 2.60]], 2.54), mats.MAT_BODY_DARK, `${name}_GLASSBAND`);
  g.add(band);
  g.add(wheelSet(mats, `${name}_WHEELS`, [-1.12, 1.12], [0, -5.60], 0.50, 0.30));
  return solid(g);
}

/** Standing / walking person, ~1.72 m, static pose, no rig. */
export function pedestrian(mats, name, opts = {}) {
  const { stride = 0.0, scale = 1 } = opts;
  const g = new THREE.Group();
  g.name = name;
  const torso = mesh(new THREE.CapsuleGeometry(0.17, 0.44, 3, 10), mats.MAT_BODY_MID, `${name}_TORSO`);
  torso.position.y = 1.14; torso.scale.set(1, 1, 0.72);
  g.add(torso);
  const head = mesh(new THREE.SphereGeometry(0.115, 12, 8), mats.MAT_BODY_MID, `${name}_HEAD`);
  head.position.y = 1.60;
  g.add(head);
  const hips = mesh(new THREE.BoxGeometry(0.32, 0.16, 0.22), mats.MAT_BODY_DARK, `${name}_HIPS`);
  hips.position.y = 0.86;
  g.add(hips);
  [[-0.10, -stride], [0.10, stride]].forEach(([x, s], i) => {
    const leg = mesh(new THREE.CapsuleGeometry(0.075, 0.60, 2, 8), mats.MAT_BODY_DARK, `${name}_LEG_${i}`);
    leg.position.set(x, 0.44, s * 0.5);
    leg.rotation.x = -s * 0.5;
    g.add(leg);
    const arm = mesh(new THREE.CapsuleGeometry(0.055, 0.46, 2, 8), mats.MAT_BODY_MID, `${name}_ARM_${i}`);
    arm.position.set(x < 0 ? -0.235 : 0.235, 1.16, -s * 0.4);
    arm.rotation.x = s * 0.4;
    g.add(arm);
  });
  g.scale.setScalar(scale);
  return solid(g);
}

/** Motorbike with rider (and optional pillion) as one compact group. */
export function motorbike(mats, name, opts = {}) {
  const { pillion = false } = opts;
  const g = new THREE.Group();
  g.name = name;
  const frame = mesh(new THREE.BoxGeometry(0.24, 0.28, 1.05), mats.MAT_BODY_DARK, `${name}_FRAME`);
  frame.position.set(0, 0.50, 0.05);
  g.add(frame);
  const tank = mesh(new THREE.BoxGeometry(0.30, 0.22, 0.46), mats.MAT_BODY_DARK, `${name}_TANK`);
  tank.position.set(0, 0.70, -0.18);
  g.add(tank);
  const fairing = mesh(new THREE.BoxGeometry(0.26, 0.44, 0.24), mats.MAT_BODY_DARK, `${name}_FAIRING`);
  fairing.position.set(0, 0.62, -0.62);
  g.add(fairing);
  const bar = mesh(new THREE.BoxGeometry(0.62, 0.05, 0.05), mats.MAT_BODY_MID, `${name}_BAR`);
  bar.position.set(0, 0.92, -0.56);
  g.add(bar);
  [[-0.66, 0.28], [0.62, 0.28]].forEach(([z, r], i) => {
    const w = wheel(mats, `${name}_WHEEL_${i}`, r, 0.10);
    w.position.set(0, r, z);
    g.add(w);
  });
  const seat = mesh(new THREE.BoxGeometry(0.30, 0.10, 0.62), mats.MAT_BODY_DARK, `${name}_SEAT`);
  seat.position.set(0, 0.78, 0.16);
  g.add(seat);
  g.add(rider(mats, `${name}_RIDER`, 0.02));
  if (pillion) g.add(rider(mats, `${name}_PILLION`, 0.44));
  return solid(g);
}

/** Seated rider: torso up, thighs forward, shins down. */
function rider(mats, name, zOffset) {
  const g = new THREE.Group();
  g.name = name;
  const torso = mesh(new THREE.CapsuleGeometry(0.16, 0.42, 3, 10), mats.MAT_BODY_MID, `${name}_TORSO`);
  torso.position.set(0, 1.14, zOffset + 0.02); torso.scale.set(1, 1, 0.72); torso.rotation.x = -0.14;
  g.add(torso);
  const head = mesh(new THREE.SphereGeometry(0.125, 12, 8), mats.MAT_BODY_MID, `${name}_HELMET`);
  head.position.set(0, 1.56, zOffset - 0.04);
  g.add(head);
  [-0.13, 0.13].forEach((x, i) => {
    const thigh = mesh(new THREE.CapsuleGeometry(0.075, 0.34, 2, 8), mats.MAT_BODY_DARK, `${name}_THIGH_${i}`);
    thigh.position.set(x, 0.80, zOffset - 0.16);
    thigh.rotation.x = Math.PI / 2 - 0.25;
    g.add(thigh);
    const shin = mesh(new THREE.CapsuleGeometry(0.065, 0.34, 2, 8), mats.MAT_BODY_DARK, `${name}_SHIN_${i}`);
    shin.position.set(x, 0.46, zOffset - 0.36);
    g.add(shin);
    const arm = mesh(new THREE.CapsuleGeometry(0.05, 0.42, 2, 8), mats.MAT_BODY_MID, `${name}_ARM_${i}`);
    arm.position.set(x < 0 ? -0.24 : 0.24, 1.08, zOffset - 0.30);
    arm.rotation.x = Math.PI / 2 - 0.55;
    g.add(arm);
  });
  return g;
}

/** Round speed-limit sign on a post — no texture, geometry only. */
export function speedSign(mats, name) {
  const g = new THREE.Group();
  g.name = name;
  const post = mesh(new THREE.CylinderGeometry(0.045, 0.045, 2.20, 8), mats.MAT_BODY_MID, `${name}_POST`);
  post.position.y = 1.10;
  g.add(post);
  const face = mesh(new THREE.CylinderGeometry(0.34, 0.34, 0.035, 24), mats.MAT_BODY_MID, `${name}_FACE`);
  face.rotation.x = Math.PI / 2;
  face.position.y = 2.20;
  g.add(face);
  const ringMat = mats.MAT_ALERT.clone();      // vành biển là mesh đặc — không trong suốt
  ringMat.name = 'MAT_ALERT';
  ringMat.transparent = false; ringMat.opacity = 1; ringMat.depthWrite = true; ringMat.side = THREE.FrontSide;
  const ring = mesh(new THREE.TorusGeometry(0.30, 0.045, 8, 24), ringMat, `${name}_RING`);
  ring.position.set(0, 2.20, 0.03);
  g.add(ring);
  // "40" as two thin plates — legible as a mark, cheap as geometry
  [-0.10, 0.10].forEach((x, i) => {
    const d = mesh(new THREE.BoxGeometry(0.11, 0.20, 0.02), mats.MAT_BODY_DARK, `${name}_DIGIT_${i}`);
    d.position.set(x, 2.20, 0.035);
    g.add(d);
  });
  return solid(g);
}

export function utilityPole(mats, name, h = 7.2) {
  const g = new THREE.Group();
  g.name = name;
  const post = mesh(new THREE.CylinderGeometry(0.11, 0.15, h, 8), mats.MAT_BODY_MID, `${name}_POST`);
  post.position.y = h / 2;
  g.add(post);
  const arm = mesh(new THREE.BoxGeometry(1.5, 0.09, 0.09), mats.MAT_BODY_MID, `${name}_ARM`);
  arm.position.set(-0.7, h - 0.5, 0);
  g.add(arm);
  return solid(g);
}

// ── Inference layer ──────────────────────────────────────────────────────
/** Truncated view pyramid from the camera origin. */
export function frustum(mats, name) {
  const hz = (deg) => Math.tan(deg * Math.PI / 360);
  const tx = hz(CAM.fovH), ty = hz(CAM.fovV);
  const pts = [];
  [CAM.near, CAM.far].forEach(d => {
    [[-1, 1], [1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => pts.push(sx * tx * d, sy * ty * d, -d));
  });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  // Chỉ 4 mặt bên — bỏ nắp gần/xa để lớp trong suốt không xếp đôi.
  geo.setIndex([
    0, 4, 5, 0, 5, 1, 1, 5, 6, 1, 6, 2,
    2, 6, 7, 2, 7, 3, 3, 7, 4, 3, 4, 0
  ]);
  geo.computeVertexNormals();
  const shell = new THREE.MeshStandardMaterial({
    color: 0x7c3aed, emissive: 0x7c3aed, emissiveIntensity: 0.15,
    transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthWrite: false
  });
  shell.name = 'MAT_INFER';
  const g = new THREE.Group();
  g.name = name;
  g.add(mesh(geo, shell, `${name}_SHELL`));
  for (let i = 0; i < 4; i++) {
    const a = new THREE.Vector3(pts[i * 3], pts[i * 3 + 1], pts[i * 3 + 2]);
    const b = new THREE.Vector3(pts[12 + i * 3], pts[13 + i * 3], pts[14 + i * 3]);
    const dir = b.clone().sub(a), len = dir.length();
    const bar = mesh(new THREE.CylinderGeometry(0.022, 0.022, len, 6), mats.MAT_INFER, `${name}_EDGE_${i}`);
    bar.position.copy(a).add(dir.clone().multiplyScalar(0.5));
    bar.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    g.add(bar);
  }
  g.rotation.x = CAM.pitch * Math.PI / 180;
  g.position.set(CAM.x, CAM.y, CAM.z);
  return noShadow(g);
}

/** Flat trapezoid strip on the ground: widthNear → widthFar over length. */
export function groundStrip(mats, name, { xCenter = 0, wNear, wFar, dNear, dFar, y, mat }) {
  const zN = zOf(dNear), zF = zOf(dFar);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute([
    xCenter - wNear / 2, 0, zN, xCenter + wNear / 2, 0, zN,
    xCenter + wFar / 2, 0, zF, xCenter - wFar / 2, 0, zF
  ], 3));
  geo.setIndex([0, 1, 2, 0, 2, 3]);
  geo.computeVertexNormals();
  const m = mesh(geo, mat || mats.MAT_INFER, name);
  m.position.y = y;
  return noShadow(m);
}

/** 8 corner brackets around a bounding box — the box is read, not drawn. */
export function bracketBox(mats, name, { w, h, l, arm = 0.22, t = 0.035, mat }) {
  const g = new THREE.Group();
  g.name = name;
  const material = mat || mats.MAT_INFER;
  let i = 0;
  [-1, 1].forEach(sx => [-1, 1].forEach(sy => [-1, 1].forEach(sz => {
    const c = [sx * w / 2, sy * h / 2, sz * l / 2];
    const dims = [[arm, t, t], [t, arm, t], [t, t, arm]];
    dims.forEach((dim, k) => {
      const b = mesh(new THREE.BoxGeometry(...dim), material, `${name}_C${i}_${'XYZ'[k]}`);
      const off = [0, 0, 0];
      off[k] = -[sx, sy, sz][k] * arm / 2;
      b.position.set(c[0] + off[0], c[1] + off[1], c[2] + off[2]);
      g.add(b);
    });
    i++;
  })));
  g.position.y = h / 2;
  return noShadow(g);
}

/** Ground arc of radius R centred on the camera origin, spanning the FOV. */
export function contourArc(mats, name, R, halfAngleDeg = 30, thickness = 0.06) {
  const a = halfAngleDeg * Math.PI / 180;
  const geo = new THREE.RingGeometry(R - thickness / 2, R + thickness / 2, 96, 1, Math.PI / 2 - a, 2 * a);
  geo.rotateX(-Math.PI / 2);
  const m = mesh(geo, mats.MAT_INFER, name);
  m.position.set(CAM.x, 0.018, CAM.z);
  return noShadow(m);
}

/** Thin ray from the camera origin toward a point. */
export function ray(mats, name, to, r = 0.02) {
  const from = new THREE.Vector3(CAM.x, CAM.y, CAM.z);
  const dir = new THREE.Vector3(...to).sub(from);
  const len = dir.length();
  const geo = new THREE.CylinderGeometry(r, r, len, 6);
  const m = mesh(geo, mats.MAT_INFER, name);
  m.position.copy(from).add(dir.clone().multiplyScalar(0.5));
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  return noShadow(m);
}

// ── Environment ──────────────────────────────────────────────────────────
export function straightRoad(mats, { width = 7.10, xMin = -5.25, length = 60, sidewalkW = 2.4, sidewalkH = 0.14, dashX = -1.75 } = {}) {
  const g = new THREE.Group();
  g.name = 'RW_A01_ENV';
  const zEnd = zOf(length), zStart = zOf(-4);
  const midZ = (zStart + zEnd) / 2, len = Math.abs(zStart - zEnd);
  const road = mesh(new THREE.PlaneGeometry(width, len, 8, 24), mats.MAT_GROUND, 'RW_A01_ENV_ROAD');
  road.rotation.x = -Math.PI / 2;
  road.position.set(xMin + width / 2, 0, midZ);
  road.receiveShadow = true;
  g.add(road);
  [['L', xMin - sidewalkW / 2], ['R', xMin + width + sidewalkW / 2]].forEach(([side, x]) => {
    const s = mesh(new THREE.BoxGeometry(sidewalkW, sidewalkH, len), mats.MAT_GROUND, `RW_A01_ENV_SIDEWALK_${side}`);
    s.position.set(x, sidewalkH / 2, midZ);
    s.castShadow = true; s.receiveShadow = true;
    g.add(s);
  });
  const dashes = new THREE.Group();
  dashes.name = 'RW_A01_ENV_LANEMARK';
  for (let d = 0; d < length; d += 9) {
    const m = mesh(new THREE.BoxGeometry(0.12, 0.01, 3.0), mats.MAT_BODY_MID, `RW_A01_ENV_LANEMARK_${d}`);
    m.position.set(dashX, 0.006, zOf(d + 1.5));
    g.add(m);
    dashes.add(m);
  }
  g.add(dashes);
  return g;
}

export function groundDisc(mats, name, R = 24) {
  const geo = new THREE.CircleGeometry(R, 64);
  geo.rotateX(-Math.PI / 2);
  const m = mesh(geo, mats.MAT_GROUND, name);
  m.position.set(0, 0, zOf(8));
  m.receiveShadow = true;
  return m;
}

export function seededRandom(seed = 7) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

export function countTriangles(root) {
  let n = 0;
  root.traverse(o => {
    if (o.isMesh && o.geometry) {
      const g = o.geometry;
      n += g.index ? g.index.count / 3 : g.attributes.position.count / 3;
    }
  });
  return Math.round(n);
}

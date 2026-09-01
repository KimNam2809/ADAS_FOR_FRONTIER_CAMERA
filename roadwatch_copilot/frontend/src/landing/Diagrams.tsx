import type { Copy } from "./content";
import { EVIDENCE } from "./content";

/* ================================================================== */
/* Sơ đồ pipeline — vẽ tay bằng SVG, không thư viện                    */
/* ================================================================== */

interface NodeProps {
  x: number; y: number; w: number; h?: number;
  label: string; tone?: "plain" | "key" | "off";
}

function N({ x, y, w, h = 40, label, tone = "plain" }: NodeProps) {
  return (
    <g className={`rw-node rw-node-${tone}`}>
      <rect x={x} y={y} width={w} height={h} rx="7" />
      <text x={x + w / 2} y={y + h / 2 + 4} textAnchor="middle">{label}</text>
    </g>
  );
}

function Edge({ d, label, lx, ly, dashed = false, anchor = "middle" }: {
  d: string; label?: string; lx?: number; ly?: number; dashed?: boolean;
  anchor?: "start" | "middle" | "end";
}) {
  return (
    <g className={`rw-edge${dashed ? " rw-edge-dashed" : ""}`}>
      <path d={d} markerEnd="url(#rw-arrow)" />
      {label && lx !== undefined && ly !== undefined ? (
        <text x={lx} y={ly} textAnchor={anchor} className="rw-edge-label">{label}</text>
      ) : null}
    </g>
  );
}

export function PipelineDiagram({ t }: { t: Copy }) {
  const n = t.pipeline.nodes;
  const e = t.pipeline.edges;
  return (
    <figure className="rw-figure">
      <svg viewBox="0 0 1160 318" role="img" aria-label={t.pipeline.aria} className="rw-diagram">
        <defs>
          <marker id="rw-arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,1 L9,5 L0,9 z" fill="currentColor" />
          </marker>
        </defs>

        {/* nguồn vào */}
        <N x={6} y={86} w={96} label={n.camera} />
        <Edge d="M104,106 H128" />
        <N x={130} y={86} w={100} label={n.gateway} />
        <text x={180} y={78} textAnchor="middle" className="rw-edge-label">{e.drop}</text>

        {/* ba model chạy độc lập, không dùng chung backbone */}
        <Edge d="M232,102 C252,102 250,50 268,50" />
        <Edge d="M232,106 H268" />
        <Edge d="M232,110 C252,110 250,162 268,162" />
        <N x={270} y={30} w={116} label={n.object} />
        <N x={270} y={86} w={116} label={n.sign} />
        <N x={270} y={142} w={116} label={n.lane} />

        {/* hợp nhất bằng bằng chứng theo thời gian */}
        <Edge d="M388,50 C408,50 406,102 424,102" />
        <Edge d="M388,106 H424" />
        <Edge d="M388,162 C408,162 406,110 424,110" />
        <text x={406} y={192} textAnchor="middle" className="rw-edge-label">{e.evidence}</text>
        <N x={426} y={86} w={98} label={n.track} />

        <Edge d="M526,106 H556" />
        <N x={558} y={86} w={98} label={n.risk} />
        <Edge d="M658,106 H688" />
        <N x={690} y={86} w={112} label={n.ctx} />

        {/* nút thắt: đúng một event được ra */}
        <Edge d="M804,106 H832" />
        <N x={834} y={80} w={112} h={52} label={n.gov} tone="key" />

        {/* đầu ra */}
        <Edge d="M948,96 C968,96 966,50 984,50" label={e.one} lx={966} ly={30} anchor="middle" />
        <Edge d="M948,116 C968,116 966,170 984,170" label={e.audit} lx={1000} ly={142} anchor="start" />
        <N x={986} y={30} w={162} label={n.out} />
        <N x={986} y={150} w={162} label={n.store} />

        {/* mọi thứ phía trên dấu ngoặc là đường quyết định */}
        <path className="rw-brace" d="M8,214 V226 H1148 V214" />
        <text x={520} y={244} textAnchor="middle" className="rw-brace-label">{t.pipeline.critical}</text>

        {/* nhánh SLM nằm ngoài đường đó */}
        <Edge d="M890,134 V258" dashed label={e.async} lx={898} ly={176} anchor="start" />
        <N x={834} y={260} w={112} label={n.slm} tone="off" />
        <text x={1000} y={286} textAnchor="start" className="rw-off-label">{t.pipeline.offPath}</text>
      </svg>
      <figcaption>{t.pipeline.caption}</figcaption>
    </figure>
  );
}

/* ================================================================== */
/* Dải độ trễ P50 → P95 qua ba phiên bản                               */
/* ================================================================== */

const W = 760;
const H = 208;
const PAD_L = 108;
const PAD_R = 34;
const MAX_MS = 260;

const x = (ms: number) => PAD_L + (ms / MAX_MS) * (W - PAD_L - PAD_R);

export function LatencyChart({ t }: { t: Copy }) {
  const rows = EVIDENCE.history;
  const gate = EVIDENCE.gates.p95;
  const rowY = (i: number) => 58 + i * 42;

  return (
    <figure className="rw-figure rw-figure-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" className="rw-chart"
        aria-label={`${t.chart.title}. ${rows.map((r) => `${r.version}: P50 ${r.p50} ms, P95 ${r.p95} ms`).join("; ")}. ${t.chart.gate}.`}>
        {/* lưới mờ */}
        {[0, 50, 100, 150, 200, 250].map((ms) => (
          <g key={ms} className="rw-grid">
            <line x1={x(ms)} y1={34} x2={x(ms)} y2={166} />
            <text x={x(ms)} y={184} textAnchor="middle">{ms}</text>
          </g>
        ))}

        {/* ngưỡng R1 — màu trạng thái, kèm nhãn chữ, không chỉ dựa vào màu */}
        <line className="rw-gate-line" x1={x(gate)} y1={28} x2={x(gate)} y2={166} />
        <text className="rw-gate-label" x={x(gate) + 7} y={22}>{t.chart.gate}</text>

        {rows.map((r, i) => {
          const y = rowY(i);
          const last = i === rows.length - 1;
          return (
            <g key={r.version} className={`rw-crow${last ? " rw-crow-now" : ""}`}>
              <title>{`${r.version} — P50 ${r.p50.toFixed(2)} ms · P95 ${r.p95.toFixed(2)} ms`}</title>
              <text className="rw-crow-name" x={PAD_L - 14} y={y + 4} textAnchor="end">{r.version}</text>
              <rect className="rw-crow-band" x={x(r.p50)} y={y - 5} width={Math.max(4, x(r.p95) - x(r.p50))} height={10} rx="4" />
              <circle className="rw-crow-dot" cx={x(r.p50)} cy={y} r="5" />
              <circle className="rw-crow-dot" cx={x(r.p95)} cy={y} r="5" />
              <text className="rw-crow-val" x={x(r.p50) - 10} y={y + 4} textAnchor="end">{r.p50.toFixed(0)}</text>
              <text className="rw-crow-val" x={x(r.p95) + 11} y={y + 4}>{r.p95.toFixed(0)}</text>
              {i === 0 ? (
                <>
                  <text className="rw-crow-key" x={x(r.p50)} y={y - 14} textAnchor="middle">{t.chart.p50}</text>
                  <text className="rw-crow-key" x={x(r.p95)} y={y - 14} textAnchor="middle">{t.chart.p95}</text>
                </>
              ) : null}
            </g>
          );
        })}
        <text className="rw-axis-title" x={W - PAD_R} y={202} textAnchor="end">{t.chart.axis}</text>
      </svg>
      <figcaption>{t.chart.note}</figcaption>
    </figure>
  );
}

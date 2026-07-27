"use client";

/** The universe-view charts: model-vs-agency two-histogram, rank scatter
 *  with SCALE_RESOLVED emphasized (shape + colour), notch-error bars.
 *  All client-rendered from the static JSON, docs/figures palette. */
import { P } from "@/lib/palette";
import type { UniverseRow } from "@/lib/schemas";
import { linScale } from "./scale";

const BANDS = ["AAA/AA", "A", "BBB", "BB", "B", "CCC"] as const;
function band(letter: string | null): string | null {
  if (!letter) return null;
  if (/^(AAA|AA)/.test(letter)) return "AAA/AA";
  if (/^A/.test(letter)) return "A";
  if (/^BBB/.test(letter)) return "BBB";
  if (/^BB/.test(letter)) return "BB";
  if (/^B/.test(letter)) return "B";
  return "CCC";
}

export function TwoHistogram({ rows }: { rows: UniverseRow[] }) {
  const model: Record<string, number> = {};
  const agency: Record<string, number> = {};
  for (const r of rows) {
    const mb = band(r.letter);
    const ab = band(r.agency_sp);
    if (mb) model[mb] = (model[mb] ?? 0) + 1;
    if (ab) agency[ab] = (agency[ab] ?? 0) + 1;
  }
  const W = 720, H = 240, M = { l: 40, r: 10, t: 24, b: 28 };
  const max = Math.max(...BANDS.map((b) => Math.max(model[b] ?? 0, agency[b] ?? 0)), 1);
  const y = linScale([0, max], [H - M.b, M.t]);
  const bw = (W - M.l - M.r) / BANDS.length;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
      aria-label="model letters versus sourced agency letters by broad grade">
      <rect width={W} height={H} fill={P.surface} rx={6} />
      {BANDS.map((b, i) => {
        const x0 = M.l + i * bw;
        const m = model[b] ?? 0;
        const a = agency[b] ?? 0;
        return (
          <g key={b}>
            {m ? (
              <g tabIndex={0} aria-label={`model ${b}: ${m}`}>
                <rect x={x0 + bw * 0.14} y={y(m)} width={bw * 0.3}
                  height={H - M.b - y(m)} rx={3} fill={P.accent} />
                <text x={x0 + bw * 0.29} y={y(m) - 4} fill={P.ink2} fontSize={10} textAnchor="middle">{m}</text>
              </g>
            ) : null}
            {a ? (
              <g tabIndex={0} aria-label={`agency ${b}: ${a}`}>
                <rect x={x0 + bw * 0.52} y={y(a)} width={bw * 0.3}
                  height={H - M.b - y(a)} rx={3} fill={P.orange} />
                <text x={x0 + bw * 0.67} y={y(a) - 4} fill={P.ink2} fontSize={10} textAnchor="middle">{a}</text>
              </g>
            ) : null}
            <text x={x0 + bw / 2} y={H - 10} fill={P.muted} fontSize={11} textAnchor="middle">{b}</text>
          </g>
        );
      })}
      <g fontSize={10} fill={P.ink2}>
        <rect x={M.l} y={6} width={10} height={10} rx={2} fill={P.accent} />
        <text x={M.l + 15} y={15}>model letters (left bar)</text>
        <rect x={M.l + 160} y={6} width={10} height={10} rx={2} fill={P.orange} />
        <text x={M.l + 175} y={15}>sourced agency (right bar)</text>
      </g>
    </svg>
  );
}

export function RankScatter({ rows }: { rows: UniverseRow[] }) {
  const NOTCHES = ["AAA","AA+","AA","AA-","A+","A","A-","BBB+","BBB","BBB-","BB+","BB","BB-","B+","B","B-","CCC+","CCC","CCC-"];
  const idx = (l: string | null) => (l ? NOTCHES.indexOf(l) : -1);
  const pts = rows
    .filter((r) => r.risk_score !== null && r.agency_sp && idx(r.agency_sp) >= 0)
    .sort((a, b) => (a.risk_score! - b.risk_score!))
    .map((r, i) => ({ ...r, mrank: i + 1 }));
  const aSorted = [...pts].sort((a, b) => idx(a.agency_sp) - idx(b.agency_sp));
  const arank = new Map(aSorted.map((r, i) => [r.ticker, i + 1]));
  const W = 380, H = 380, M2 = 36;
  const s = linScale([0, pts.length + 1], [M2, W - 10]);
  const t = linScale([0, pts.length + 1], [H - M2, 10]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
      aria-label="RiskScore rank versus agency rank; scale-resolved names emphasized">
      <rect width={W} height={H} fill={P.surface} rx={6} />
      <line x1={s(0)} y1={t(0)} x2={s(pts.length)} y2={t(pts.length)} stroke={P.grid} />
      {pts.map((r) => {
        const resolved = r.determination === "SCALE_RESOLVED";
        const cx = s(r.mrank), cy = t(arank.get(r.ticker) ?? 0);
        return resolved ? (
          <circle key={r.ticker} cx={cx} cy={cy} r={5} fill={P.accent}
            stroke={P.surface} strokeWidth={1.4} tabIndex={0}
            aria-label={`${r.ticker} model rank ${r.mrank}, agency rank ${arank.get(r.ticker)}, scale resolved`}>
            <title>{r.ticker}</title>
          </circle>
        ) : (
          <circle key={r.ticker} cx={cx} cy={cy} r={3.5} fill="none" stroke={P.muted}
            strokeWidth={1.2} tabIndex={0}
            aria-label={`${r.ticker} model rank ${r.mrank}, agency rank ${arank.get(r.ticker)}`}>
            <title>{r.ticker}</title>
          </circle>
        );
      })}
      <text x={W / 2} y={H - 8} fill={P.ink2} fontSize={10} textAnchor="middle">
        RiskScore rank (safe → risky)
      </text>
      <text x={12} y={H / 2} fill={P.ink2} fontSize={10} textAnchor="middle"
        transform={`rotate(-90 12 ${H / 2})`}>
        agency rank
      </text>
      <g fontSize={9.5} fill={P.ink2}>
        <circle cx={M2 + 6} cy={14} r={5} fill={P.accent} />
        <text x={M2 + 15} y={17}>SCALE_RESOLVED</text>
        <circle cx={M2 + 116} cy={14} r={3.5} fill="none" stroke={P.muted} strokeWidth={1.2} />
        <text x={M2 + 124} y={17}>pinned / other</text>
      </g>
    </svg>
  );
}

export function NotchErrors({ errors }: { errors: number[] }) {
  const counts = new Map<number, number>();
  for (const e of errors) counts.set(e, (counts.get(e) ?? 0) + 1);
  const keys = [...counts.keys()].sort((a, b) => a - b);
  if (!keys.length) return null;
  const W = 380, H = 240, M2 = { l: 30, r: 8, t: 16, b: 30 };
  const max = Math.max(...counts.values());
  const y = linScale([0, max], [H - M2.b, M2.t]);
  const bw = (W - M2.l - M2.r) / (keys[keys.length - 1] - keys[0] + 1);
  const x0 = (k: number) => M2.l + (k - keys[0]) * bw;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
      aria-label="notch error distribution, positive means the model is optimistic">
      <rect width={W} height={H} fill={P.surface} rx={6} />
      {keys.map((k) => (
        <g key={k} tabIndex={0} aria-label={`error ${k}: ${counts.get(k)} companies`}>
          <rect x={x0(k) + 1.5} y={y(counts.get(k)!)} width={bw - 3}
            height={H - M2.b - y(counts.get(k)!)} rx={2} fill={P.accent} />
          <text x={x0(k) + bw / 2} y={H - 14} fill={P.muted} fontSize={9} textAnchor="middle">{k}</text>
        </g>
      ))}
      <line x1={x0(0) + bw / 2 - bw / 2} x2={x0(0)} y1={M2.t} y2={H - M2.b} stroke={P.ink2} strokeWidth={1} />
      <text x={W / 2} y={H - 2} fill={P.ink2} fontSize={9.5} textAnchor="middle">
        notch error (agency − model; + = model optimistic)
      </text>
    </svg>
  );
}

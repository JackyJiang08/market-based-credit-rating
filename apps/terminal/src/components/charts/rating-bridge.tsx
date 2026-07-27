"use client";

/** PIT → TTC → letter waterfall: what the conversion did, and whether a
 *  floor or the scale top bound the result. PD stages on a log axis. */
import { P } from "@/lib/palette";
import { letterWithInterval, pct } from "@/lib/format";
import type { CompanyDetail } from "@/lib/schemas";
import { logScale, logTicks } from "./scale";

const W = 720;
const H = 190;
const M = { l: 120, r: 210, t: 14, b: 30 };
const DOM: [number, number] = [1e-7, 1];

export function RatingBridge({ d }: { d: CompanyDetail }) {
  const x = logScale(DOM, [M.l, W - M.r]);
  const pit = d.measures.pit_pd;
  const ttc = d.measures.ttc_pd;
  const clamp = (v: number) => Math.min(Math.max(v, DOM[0]), DOM[1]);
  const bound = d.rating.at_floor
    ? "floor bound the result (grid's smallest value)"
    : d.rating.at_scale_top
      ? "scale top bound the result (best published grade)"
      : null;

  if (pit === null)
    return (
      <div className="rounded border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-zinc-400">
        No PD chain for this company ({d.drift.regime === "DEFECTIVE"
          ? "defective drift regime"
          : d.applicability.reason_code ?? "no estimates"}).
      </div>
    );

  const stages = [
    { label: "PIT PD (market-implied, 1y)", v: pit, tone: P.muted },
    ...(ttc !== null
      ? [{ label: "TTC PD (no-arbitrage conversion)", v: ttc, tone: P.accent }]
      : []),
  ];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="group"
      aria-label="rating bridge from PIT PD to TTC PD to the letter">
      <rect width={W} height={H} fill={P.surface} rx={6} />
      {logTicks(DOM).map((v) => (
        <g key={v}>
          <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} stroke={P.grid} />
          <text x={x(v)} y={H - 10} fill={P.muted} fontSize={9} textAnchor="middle">
            {v.toExponential(0)}
          </text>
        </g>
      ))}
      {stages.map((s, i) => {
        const yv = M.t + ((i + 0.5) / 2) * (H - M.t - M.b);
        return (
          <g key={s.label} tabIndex={0} aria-label={`${s.label}: ${pct(s.v, 4)}`}>
            <text x={M.l - 8} y={yv + 3} fill={P.ink2} fontSize={10} textAnchor="end">
              {s.label}
            </text>
            <line x1={M.l} x2={W - M.r} y1={yv} y2={yv} stroke={P.grid} />
            <circle cx={x(clamp(s.v))} cy={yv} r={5.5} fill={s.tone}
              stroke={P.surface} strokeWidth={1.5} />
            <text x={x(clamp(s.v)) + 9} y={yv + 3} fill={P.ink} fontSize={10}>
              {pct(s.v, 4)}
            </text>
          </g>
        );
      })}
      {stages.length === 2 ? (
        <line
          x1={x(clamp(stages[0].v))}
          y1={M.t + 0.25 * (H - M.t - M.b) + 6}
          x2={x(clamp(stages[1].v))}
          y2={M.t + 0.75 * (H - M.t - M.b) - 6}
          stroke={P.base}
          strokeWidth={1.2}
          markerEnd="url(#arr)"
        />
      ) : null}
      <defs>
        <marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0L8,4L0,8Z" fill={P.base} />
        </marker>
      </defs>
      <g transform={`translate(${W - M.r + 10}, ${M.t + 6})`}>
        <text fill={P.ink2} fontSize={10}>letter (derived conversion):</text>
        <text y={18} fill={P.ink} fontSize={13} fontWeight={600} className="font-mono">
          {letterWithInterval(d.rating.letter, d.rating.interval_low, d.rating.interval_high)}
        </text>
        <text y={34} fill={P.muted} fontSize={9.5}>
          {d.rating.basis ?? "no basis"} · {d.rating.determination ?? "—"}
        </text>
        {bound ? (
          <text y={50} fill={P.rampLight} fontSize={9.5}>⚠ {bound}</text>
        ) : ttc !== null ? (
          <text y={50} fill={P.muted} fontSize={9.5}>scale resolved the value</text>
        ) : (
          <text y={50} fill={P.muted} fontSize={9.5}>no TTC (conversion unavailable)</text>
        )}
      </g>
    </svg>
  );
}

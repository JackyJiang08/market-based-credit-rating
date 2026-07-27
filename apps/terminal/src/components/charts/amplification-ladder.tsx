"use client";

/** The x4,077 finding as a picture: relative 5-95 interval width per
 *  quantity, log scale — per company (accent) against the universe median
 *  (open markers). Dot ladder, not bars: bar length lies on a log axis. */
import { P } from "@/lib/palette";
import { fmt } from "@/lib/format";
import { logScale, logTicks } from "./scale";

const ROWS: { key: keyof Widths; label: string }[] = [
  { key: "sigma_a", label: "σ_A (input)" },
  { key: "risk_score", label: "RiskScore (drift-free)" },
  { key: "dd", label: "DD" },
  { key: "ttc_pd", label: "TTC PD" },
  { key: "pit_pd", label: "PIT PD" },
];
type Widths = {
  sigma_a: number | null;
  risk_score: number | null;
  dd: number | null;
  ttc_pd: number | null;
  pit_pd: number | null;
};

const W = 720;
const H = 220;
const M = { l: 170, r: 90, t: 10, b: 30 };
const DOM: [number, number] = [0.05, 20000];

export function AmplificationLadder({
  company,
  companyTicker,
  median,
}: {
  company: Widths | null;
  companyTicker?: string;
  median: Widths | null;
}) {
  const x = logScale(DOM, [M.l, W - M.r]);
  const rowY = (i: number) => M.t + ((i + 0.5) / ROWS.length) * (H - M.t - M.b);
  const amp =
    company?.pit_pd && company?.risk_score
      ? company.pit_pd / company.risk_score
      : median?.pit_pd && median?.risk_score
        ? median.pit_pd / median.risk_score
        : null;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
      aria-label="relative bootstrap interval width per quantity, log scale">
      <rect width={W} height={H} fill={P.surface} rx={6} />
      {logTicks(DOM).map((v) => (
        <g key={v}>
          <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} stroke={P.grid} />
          <text x={x(v)} y={H - 10} fill={P.muted} fontSize={10} textAnchor="middle">
            {v >= 1 ? v.toLocaleString() : v}
          </text>
        </g>
      ))}
      {ROWS.map((r, i) => {
        const yv = rowY(i);
        const c = company?.[r.key];
        const m = median?.[r.key];
        return (
          <g key={r.key}>
            <text x={M.l - 8} y={yv + 3} fill={P.ink2} fontSize={11} textAnchor="end">
              {r.label}
            </text>
            <line x1={M.l} x2={W - M.r} y1={yv} y2={yv} stroke={P.grid} />
            {m ? (
              <circle cx={x(m)} cy={yv} r={4.5} fill="none" stroke={P.muted}
                strokeWidth={1.5}>
                <title>universe median {fmt(m, 3)}</title>
              </circle>
            ) : null}
            {c ? (
              <g tabIndex={0} aria-label={`${r.label}: ${fmt(c, 3)}`}>
                <circle cx={x(c)} cy={yv} r={5.5} fill={P.accent}
                  stroke={P.surface} strokeWidth={1.5} />
                <text x={x(c) + 9} y={yv + 3} fill={P.ink} fontSize={10}>
                  {c < 10 ? fmt(c, 3) : `~${fmt(c, 0)}`}
                </text>
              </g>
            ) : (
              <text x={W - M.r + 8} y={yv + 3} fill={P.muted} fontSize={10}>
                n/a
              </text>
            )}
          </g>
        );
      })}
      <g fontSize={10} fill={P.ink2}>
        <circle cx={M.l + 8} cy={H - 22} r={5} fill={P.accent} />
        <text x={M.l + 18} y={H - 19}>{companyTicker ?? "company"}</text>
        <circle cx={M.l + 108} cy={H - 22} r={4.5} fill="none" stroke={P.muted} strokeWidth={1.5} />
        <text x={M.l + 118} y={H - 19}>universe median (147 names)</text>
        {amp ? (
          <text x={W - M.r} y={H - 19} textAnchor="end" fill={P.ink}>
            RiskScore → PIT amplification: ×{fmt(amp, 0)}
          </text>
        ) : null}
      </g>
    </svg>
  );
}

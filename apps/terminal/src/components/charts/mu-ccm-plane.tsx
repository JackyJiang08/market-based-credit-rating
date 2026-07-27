"use client";

/** The signature visual: the ln(µ)–ln(CCM) plane.
 *
 * Iso-rating lines have slope Q (S&P system, Q = 0.625913) at the published
 * Table-8 RiskScores; the published grid-domain box and the scale-top region
 * are drawn so pinned positions are visually obvious. Companies are encoded
 * by SHAPE as well as colour (never colour-only): SCALE_RESOLVED = filled
 * circle, pinned = open diamond, everything else = open circle. Hover or
 * focus any point for the company card; enter/click navigates.
 */
import { GRID_DOMAIN, P, Q_SP, SP_SCALE } from "@/lib/palette";
import type { UniverseRow } from "@/lib/schemas";
import { fmt } from "@/lib/format";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { logScale, logTicks } from "./scale";

const W = 760;
const H = 480;
const M = { l: 52, r: 130, t: 16, b: 40 };
const MU: [number, number] = [0.5, 4000];
const CCM: [number, number] = [0.005, 1000];

export function MuCcmPlane({
  rows,
  cloud,
  focusTicker,
}: {
  rows: (UniverseRow & { mu?: number | null; ccm?: number | null })[];
  cloud?: { mu: number; ccm: number }[];
  focusTicker?: string;
}) {
  const [hover, setHover] = useState<UniverseRow | null>(null);
  const router = useRouter();
  const x = logScale(MU, [M.l, W - M.r]);
  const y = logScale(CCM, [H - M.b, M.t]);

  const pts = rows.filter(
    (r) => r.mu && r.ccm && r.mu > MU[0] && r.mu < MU[1] && r.ccm > CCM[0] && r.ccm < CCM[1],
  );

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label="ln mu versus ln CCM plane with iso-rating lines of slope Q"
      >
        <rect width={W} height={H} fill={P.surface} rx={6} />
        {/* published grid-domain box: inside = lookup, outside = analytical */}
        <rect
          x={x(GRID_DOMAIN.mu[0])}
          y={y(GRID_DOMAIN.ccm[1])}
          width={x(GRID_DOMAIN.mu[1]) - x(GRID_DOMAIN.mu[0])}
          height={y(GRID_DOMAIN.ccm[0]) - y(GRID_DOMAIN.ccm[1])}
          fill={P.accent}
          fillOpacity={0.05}
          stroke={P.base}
          strokeDasharray="4 3"
        />
        <text x={x(GRID_DOMAIN.mu[0]) + 6} y={y(GRID_DOMAIN.ccm[1]) + 14} fill={P.muted} fontSize={10}>
          lookup-grid domain (published axes) — outside: analytical route
        </text>

        {/* axes */}
        {logTicks(MU).map((v) => (
          <g key={`x${v}`}>
            <line x1={x(v)} x2={x(v)} y1={M.t} y2={H - M.b} stroke={P.grid} />
            <text x={x(v)} y={H - M.b + 16} fill={P.muted} fontSize={10} textAnchor="middle">
              {v >= 1 ? v.toLocaleString() : v}
            </text>
          </g>
        ))}
        {logTicks(CCM).map((v) => (
          <g key={`y${v}`}>
            <line y1={y(v)} y2={y(v)} x1={M.l} x2={W - M.r} stroke={P.grid} />
            <text x={M.l - 6} y={y(v) + 3} fill={P.muted} fontSize={10} textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        <text x={(M.l + W - M.r) / 2} y={H - 8} fill={P.ink2} fontSize={11} textAnchor="middle">
          µ (life expectancy, log)
        </text>
        <text
          x={14}
          y={(M.t + H - M.b) / 2}
          fill={P.ink2}
          fontSize={11}
          textAnchor="middle"
          transform={`rotate(-90 14 ${(M.t + H - M.b) / 2})`}
        >
          CCM (log)
        </text>

        {/* iso-rating lines, slope Q in ln-ln: CCM = (RS/100) * mu^Q */}
        {SP_SCALE.map(({ letter, rs }, i) => {
          const f = (mu: number) => (rs / 100) * Math.pow(mu, Q_SP);
          const seg: [number, number][] = [];
          for (let t = 0; t <= 40; t++) {
            const mu = MU[0] * Math.pow(MU[1] / MU[0], t / 40);
            const c = f(mu);
            if (c >= CCM[0] && c <= CCM[1]) seg.push([x(mu), y(c)]);
          }
          if (seg.length < 2) return null;
          return (
            <g key={letter}>
              <path
                d={seg.map(([px, py], j) => `${j ? "L" : "M"}${px},${py}`).join("")}
                fill="none"
                stroke={i === 0 ? P.ink2 : P.base}
                strokeWidth={i === 0 ? 1.4 : 1}
              />
              <text x={seg[seg.length - 1][0] + 4} y={seg[seg.length - 1][1] + 3} fill={P.ink2} fontSize={10}>
                {letter} ({rs})
              </text>
            </g>
          );
        })}
        {/* scale-top: below the AAA iso line the letter is pinned */}
        <text x={W - M.r - 4} y={H - M.b - 8} fill={P.muted} fontSize={10} textAnchor="end">
          below AAA iso line → PINNED_AT_SCALE_TOP
        </text>

        {/* bootstrap cloud for the focused company */}
        {cloud?.map((p, i) =>
          p.mu > MU[0] && p.mu < MU[1] && p.ccm > CCM[0] && p.ccm < CCM[1] ? (
            <circle
              key={i}
              cx={x(p.mu)}
              cy={y(p.ccm)}
              r={2}
              fill={P.accent}
              fillOpacity={0.22}
            />
          ) : null,
        )}

        {/* companies: shape + colour, never colour alone */}
        {pts.map((r) => {
          const cx = x(r.mu!);
          const cy = y(r.ccm!);
          const resolved = r.determination === "SCALE_RESOLVED";
          const pinned = r.determination?.startsWith("PINNED");
          const isFocus = r.ticker === focusTicker;
          const common = {
            tabIndex: 0,
            role: "button" as const,
            "aria-label": `${r.ticker}: mu ${fmt(r.mu, 1)}, CCM ${fmt(r.ccm, 3)}, ${r.determination ?? "no determination"}`,
            onMouseEnter: () => setHover(r),
            onMouseLeave: () => setHover(null),
            onFocus: () => setHover(r),
            onBlur: () => setHover(null),
            onClick: () => router.push(`/company/${r.ticker}/`),
            onKeyDown: (e: React.KeyboardEvent) => {
              if (e.key === "Enter") router.push(`/company/${r.ticker}/`);
            },
            style: { cursor: "pointer", outline: "none" },
          };
          if (resolved)
            return (
              <circle key={r.ticker} cx={cx} cy={cy} r={isFocus ? 7 : 5}
                fill={P.accent} stroke={P.surface} strokeWidth={1.5} {...common} />
            );
          if (pinned)
            return (
              <path key={r.ticker}
                d={`M${cx},${cy - 6}L${cx + 6},${cy}L${cx},${cy + 6}L${cx - 6},${cy}Z`}
                fill="none" stroke={P.rampLight} strokeWidth={1.8} {...common} />
            );
          return (
            <circle key={r.ticker} cx={cx} cy={cy} r={4.5}
              fill="none" stroke={P.muted} strokeWidth={1.5} {...common} />
          );
        })}

        {/* legend: shape + label */}
        <g transform={`translate(${W - M.r + 10}, ${H - 130})`} fontSize={10} fill={P.ink2}>
          <circle cx={6} cy={4} r={5} fill={P.accent} />
          <text x={16} y={7}>SCALE_RESOLVED</text>
          <path d="M1,24L7,18L13,24L7,30Z" fill="none" stroke={P.rampLight} strokeWidth={1.6} />
          <text x={16} y={27}>pinned (floor/top)</text>
          <circle cx={6} cy={44} r={4.5} fill="none" stroke={P.muted} strokeWidth={1.5} />
          <text x={16} y={47}>other / gated</text>
        </g>
      </svg>

      {hover ? (
        <div
          role="status"
          className="pointer-events-none absolute left-2 top-2 rounded border border-zinc-700 bg-zinc-900/95 p-2 font-mono text-[11px] leading-snug shadow-lg"
        >
          <div className="font-semibold text-zinc-100">
            {hover.ticker} <span className="font-normal text-zinc-400">{hover.name}</span>
          </div>
          <div>µ {fmt(hover.mu, 1)} · CCM {fmt(hover.ccm, 4)} · RS {fmt(hover.risk_score, 2)}</div>
          <div className="text-zinc-400">
            {hover.letter
              ? `${hover.letter} (${hover.interval_low}..${hover.interval_high})`
              : hover.determination}
            {" · "}
            {hover.basis ?? "—"}
          </div>
        </div>
      ) : null}
    </div>
  );
}

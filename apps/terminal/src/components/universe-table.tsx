"use client";

/** The universe table. Defaults a designer would pick: rated names first by
 *  rank; names without estimates grouped at the BOTTOM behind a subdued
 *  divider linking to the failure taxonomy; sticky header; right-aligned
 *  tabular numerics. Collapses to cards on mobile. */
import { ChipRow } from "@/components/flag-chips";
import { RatingCell } from "@/components/rating-cell";
import { enumLabel } from "@/lib/labels";
import { fmt } from "@/lib/format";
import type { UniverseRow } from "@/lib/schemas";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

type SortKey = "risk_rank" | "ticker" | "risk_score" | "sigma_a" | "dd";

const TAXONOMY_URL =
  "https://github.com/JackyJiang08/market-based-credit-rating/blob/main/docs/UNIVERSE.md#failure-taxonomy";

function flagsFor(r: UniverseRow): string[] {
  const out: string[] = [];
  if (r.applicability_reason) out.push(r.applicability_reason);
  if (r.weakly_identified) out.push("WEAKLY_IDENTIFIED");
  return out;
}

export function UniverseTable({ rows, initialLimit }: { rows: UniverseRow[]; initialLimit?: number }) {
  const [showAll, setShowAll] = useState(initialLimit === undefined);
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({
    key: "risk_rank",
    desc: false,
  });
  const router = useRouter();

  const { withEst, withoutEst } = useMemo(() => {
    const w = rows.filter((r) => r.risk_score !== null);
    const wo = rows.filter((r) => r.risk_score === null);
    const dir = sort.desc ? -1 : 1;
    w.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      return av < bv ? -dir : av > bv ? dir : 0;
    });
    return { withEst: w, withoutEst: wo };
  }, [rows, sort]);

  const visible = showAll ? withEst : withEst.slice(0, initialLimit ?? withEst.length);
  const go = (t: string) => router.push(`/company/${t}/`);

  const header = (key: SortKey, label: string, numeric = false) => (
    <th
      className={`sticky top-[46px] z-10 bg-zinc-950/95 px-2 py-1.5 font-medium text-zinc-400 backdrop-blur ${numeric ? "text-right" : "text-left"}`}
      aria-sort={sort.key === key ? (sort.desc ? "descending" : "ascending") : "none"}
    >
      <button
        className="hover:text-zinc-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        onClick={() => setSort((s) => ({ key, desc: s.key === key ? !s.desc : false }))}
      >
        {label}
        <span aria-hidden className="ml-0.5 inline-block w-3 text-sky-300">
          {sort.key === key ? (sort.desc ? "▼" : "▲") : ""}
        </span>
      </button>
    </th>
  );

  return (
    <div>
      {/* desktop: the table */}
      <table className="hidden w-full border-collapse text-[13px] md:table">
        <thead>
          <tr className="border-b border-zinc-700">
            {header("risk_rank", "Rank", true)}
            {header("ticker", "Ticker")}
            <th className="sticky top-[46px] z-10 bg-zinc-950/95 px-2 py-1.5 text-left font-medium text-zinc-400 backdrop-blur">
              Company
            </th>
            {header("risk_score", "RiskScore", true)}
            {header("sigma_a", "σ_A", true)}
            {header("dd", "DD", true)}
            <th className="sticky top-[46px] z-10 bg-zinc-950/95 px-2 py-1.5 text-left font-medium text-zinc-400 backdrop-blur">
              Letter (interval)
            </th>
            <th className="sticky top-[46px] z-10 bg-zinc-950/95 px-2 py-1.5 text-left font-medium text-zinc-400 backdrop-blur">
              Determination
            </th>
            <th className="sticky top-[46px] z-10 bg-zinc-950/95 px-2 py-1.5 text-left font-medium text-zinc-400 backdrop-blur">
              Flags
            </th>
          </tr>
        </thead>
        <tbody>
          {visible.map((r) => (
            <tr
              key={r.ticker}
              tabIndex={0}
              className="cursor-pointer border-b border-zinc-800/70 hover:bg-zinc-800/50 focus:outline-none focus-visible:bg-zinc-800/70"
              onClick={() => go(r.ticker)}
              onKeyDown={(e) => e.key === "Enter" && go(r.ticker)}
            >
              <td className="px-2 py-1 text-right font-mono tabular-nums text-zinc-400">
                {fmt(r.risk_rank, 0)}
              </td>
              <td className="px-2 py-1 font-mono font-semibold text-zinc-100">{r.ticker}</td>
              <td className="px-2 py-1 text-zinc-300">
                {r.name ?? "—"}
                {r.delisted ? <span className="ml-1 text-[11px] text-zinc-400">(delisted)</span> : null}
              </td>
              <td className="px-2 py-1 text-right font-mono tabular-nums text-sky-300">
                {fmt(r.risk_score, 3)}
              </td>
              <td className="px-2 py-1 text-right font-mono tabular-nums">{fmt(r.sigma_a, 3)}</td>
              <td className="px-2 py-1 text-right font-mono tabular-nums">{fmt(r.dd, 2)}</td>
              <td className="px-2 py-1">
                <RatingCell
                  letter={r.letter}
                  lo={r.interval_low}
                  hi={r.interval_high}
                  notches={r.interval_notches}
                  basis={r.basis}
                  determination={r.determination}
                />
              </td>
              <td className="px-2 py-1 text-xs text-zinc-400">{enumLabel(r.determination).label}</td>
              <td className="px-2 py-1">
                <ChipRow codes={flagsFor(r)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* mobile: cards */}
      <ul className="space-y-2 md:hidden" aria-label="universe (cards)">
        {visible.map((r) => (
          <li key={r.ticker}>
            <button
              className="w-full rounded-md border border-zinc-800 bg-zinc-900/60 p-3 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              onClick={() => go(r.ticker)}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-mono font-semibold text-zinc-100">
                  {r.ticker}
                  <span className="ml-2 text-xs font-normal text-zinc-400">
                    #{fmt(r.risk_rank, 0)}
                  </span>
                </span>
                <span className="font-mono tabular-nums text-sky-300">{fmt(r.risk_score, 3)}</span>
              </div>
              <div className="mt-0.5 truncate text-xs text-zinc-400">{r.name}</div>
              <div className="mt-1.5 flex items-center justify-between gap-2">
                <RatingCell
                  letter={r.letter}
                  lo={r.interval_low}
                  hi={r.interval_high}
                  determination={r.determination}
                />
                <ChipRow codes={flagsFor(r)} max={1} />
              </div>
            </button>
          </li>
        ))}
      </ul>

      {!showAll && withEst.length > (initialLimit ?? 0) ? (
        <button
          className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-900 py-1.5 text-xs text-zinc-300 hover:border-zinc-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          onClick={() => setShowAll(true)}
        >
          show all {withEst.length} names with estimates (first {initialLimit} shown)
        </button>
      ) : null}

      {withoutEst.length ? (
        <div className="mt-4">
          <div className="mb-1.5 flex items-center gap-2 text-xs text-zinc-400">
            <span className="h-px flex-1 bg-zinc-800" aria-hidden />
            <a
              className="underline decoration-zinc-600 underline-offset-2 hover:text-zinc-200"
              href={TAXONOMY_URL}
            >
              {withoutEst.length} names without estimates — why?
            </a>
            <span className="h-px flex-1 bg-zinc-800" aria-hidden />
          </div>
          <ul className="flex flex-wrap gap-1.5 text-xs" aria-label="names without estimates">
            {withoutEst.map((r) => (
              <li
                key={r.ticker}
                className="rounded border border-zinc-800 bg-zinc-900/50 px-2 py-1 font-mono text-zinc-400"
                title={r.taxonomy_detail ?? undefined}
              >
                {r.ticker}
                {r.delisted ? " (delisted)" : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

import fs from "node:fs";
import path from "node:path";
import Link from "next/link";
import type { Universe, UniverseRow } from "@/lib/schemas";

const REPO = "https://github.com/JackyJiang08/market-based-credit-rating";

function universeAtBuildTime(): Universe {
  const p = path.join(process.cwd(), "public", "data", "universe.json");
  return JSON.parse(fs.readFileSync(p, "utf-8")) as Universe;
}

function StatCard({
  value,
  label,
  href,
  external = false,
}: {
  value: string;
  label: string;
  href: string;
  external?: boolean;
}) {
  const inner = (
    <span className="block rounded-lg border border-zinc-800 bg-zinc-900/60 p-4 transition-colors hover:border-zinc-600 focus:outline-none">
      <span className="block font-mono text-2xl font-semibold tabular-nums text-sky-300">
        {value}
      </span>
      <span className="mt-1 block text-xs leading-snug text-zinc-400">{label}</span>
    </span>
  );
  return external ? (
    <a href={href} className="focus-visible:ring-2 focus-visible:ring-sky-400">{inner}</a>
  ) : (
    <Link href={href} className="focus-visible:ring-2 focus-visible:ring-sky-400">{inner}</Link>
  );
}

function TopStrip({ title, rows }: { title: string; rows: UniverseRow[] }) {
  return (
    <div>
      <h2 className="mb-1.5 text-sm font-medium text-zinc-300">{title}</h2>
      <ol className="divide-y divide-zinc-800/70 rounded-lg border border-zinc-800 bg-zinc-900/40">
        {rows.map((r) => (
          <li key={r.ticker}>
            <Link
              href={`/company/${r.ticker}/`}
              className="flex items-baseline gap-2 px-3 py-1.5 text-[13px] hover:bg-zinc-800/50 focus:outline-none focus-visible:bg-zinc-800/70"
            >
              <span className="w-8 text-right font-mono tabular-nums text-zinc-400">
                {r.risk_rank}
              </span>
              <span className="w-14 font-mono font-semibold text-zinc-100">{r.ticker}</span>
              <span className="min-w-0 flex-1 truncate text-zinc-400">{r.name}</span>
              <span className="font-mono tabular-nums text-sky-300">
                {r.risk_score?.toFixed(2)}
              </span>
              <span className="w-28 truncate text-right font-mono text-xs text-zinc-400">
                {r.letter ? `${r.letter} (${r.interval_low}..${r.interval_high})` : "—"}
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function Home() {
  const universe = universeAtBuildTime();
  const withEst = universe.rows
    .filter((r): r is UniverseRow & { risk_score: number } => r.risk_score !== null)
    .sort((a, b) => a.risk_score - b.risk_score);
  const safest = withEst.slice(0, 10);
  const riskiest = withEst.slice(-10).reverse();

  return (
    <div className="space-y-8">
      {/* hero */}
      <section className="pt-6 text-center">
        <h1 className="mx-auto max-w-2xl text-2xl font-semibold leading-snug text-zinc-50">
          Market-based credit ratings with honest uncertainty —{" "}
          <span className="text-sky-300">150 companies, computed offline</span>
        </h1>
        <p className="mt-2 text-sm text-zinc-400">
          KMV/Merton structural model → Time-Consistent measures → a letter that never
          travels without its interval. Press <kbd className="font-mono">⌘K</kbd> or{" "}
          <kbd className="font-mono">/</kbd>, or use the search box above.
        </p>
      </section>

      {/* the four numbers that are the project */}
      <section aria-label="headline results" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard value="ρ = 0.79" label="rank correlation against sourced agency ratings (0.73 restricted to scale-resolved names)" href={`${REPO}/blob/main/docs/analysis/VALIDATION.md`} external />
        <StatCard value="×4,073" label="how much the PD-based letter layer amplifies parameter uncertainty vs the drift-free RiskScore" href={`${REPO}/blob/main/docs/UNCERTAINTY.md`} external />
        <StatCard value="τ = 0.956" label="ordering stability across 2,000 bootstrap replicates — the extremes are never misordered" href={`${REPO}/blob/main/docs/UNCERTAINTY.md`} external />
        <StatCard value="+5 notches" label="how optimistic the letter runs against agency ratings — the conversion, not the ordering, is the weak layer" href="/validation/" />
      </section>

      {/* the AAA question, answered before it is asked */}
      <section
        aria-label="why is everything AAA"
        className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-4 text-sm leading-relaxed text-zinc-300"
      >
        <strong className="text-sky-300">Why does every big name show AAA?</strong>{" "}
        That is the finding, not a bug. For large liquid investment-grade firms a
        market-implied one-year default probability is smaller than anything a rating
        scale can express, so the letter pins at the scale&apos;s ceiling — 60% of rated
        names land there, which is exactly why this project leads with RiskScore and
        the rank ordering instead of the letter.{" "}
        <a
          className="underline decoration-sky-500/60 underline-offset-2 hover:text-sky-200"
          href={`${REPO}/blob/main/README.md#scale-resolution`}
        >
          Scale resolution →
        </a>
      </section>

      {/* top strips */}
      <section className="grid gap-4 lg:grid-cols-2">
        <TopStrip title="Safest 10 by RiskScore" rows={safest} />
        <TopStrip title="Riskiest 10 by RiskScore" rows={riskiest} />
      </section>

      <div className="text-center">
        <Link
          href="/universe/"
          className="inline-block rounded-md border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm text-zinc-200 hover:border-zinc-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        >
          Full universe — all 150 names, filters and charts →
        </Link>
      </div>
    </div>
  );
}

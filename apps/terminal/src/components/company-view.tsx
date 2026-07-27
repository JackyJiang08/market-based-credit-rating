"use client";

/** Company view: header, RiskScore-first result table, interval-attached
 *  letter, provenance popovers, first-class flag chips, EM path sparkline. */
import { FlagChip } from "@/components/flag-chips";
import { RatingCell } from "@/components/rating-cell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { loadCompany, loadUniverse } from "@/lib/data";
import { big, fmt, pct } from "@/lib/format";
import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AmplificationLadder } from "@/components/charts/amplification-ladder";
import { MuCcmPlane } from "@/components/charts/mu-ccm-plane";
import { RatingBridge } from "@/components/charts/rating-bridge";
import { loadValidation } from "@/lib/data";

function Prov({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Popover>
      <PopoverTrigger
        className="inline-flex items-center gap-1 text-zinc-500 hover:text-zinc-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        aria-label={`provenance for ${label}`}
      >
        <Info className="h-3 w-3" aria-hidden />
      </PopoverTrigger>
      <PopoverContent className="w-80 text-xs leading-relaxed">{children}</PopoverContent>
    </Popover>
  );
}

function Row({
  label,
  value,
  prov,
  emphasis = false,
}: {
  label: string;
  value: React.ReactNode;
  prov?: React.ReactNode;
  emphasis?: boolean;
}) {
  return (
    <tr className="border-b border-zinc-800/60">
      <td className="py-1 pr-4 text-zinc-400">
        {label} {prov}
      </td>
      <td
        className={`py-1 text-right font-mono tabular-nums ${
          emphasis ? "text-base font-semibold text-sky-300" : "text-zinc-100"
        }`}
      >
        {value}
      </td>
    </tr>
  );
}

function Spark({ points }: { points: { date: string; asset_value: number }[] }) {
  if (points.length < 2) return null;
  const vals = points.map((p) => p.asset_value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const W = 640;
  const H = 80;
  const path = vals
    .map(
      (v, i) =>
        `${i === 0 ? "M" : "L"}${((i / (vals.length - 1)) * W).toFixed(1)},${(
          H -
          ((v - min) / (max - min || 1)) * (H - 8) -
          4
        ).toFixed(1)}`,
    )
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="h-20 w-full"
      role="img"
      aria-label={`EM-implied asset value path, ${points[0].date} to ${points[points.length - 1].date}`}
    >
      <path d={path} fill="none" stroke="#7dd3fc" strokeWidth="1.5" />
    </svg>
  );
}

export function CompanyView({ ticker }: { ticker: string }) {
  const detail = useQuery({
    queryKey: ["company", ticker],
    queryFn: () => loadCompany(ticker),
    retry: false,
  });
  const uni = useQuery({ queryKey: ["universe"], queryFn: loadUniverse });
  const val = useQuery({ queryKey: ["validation"], queryFn: loadValidation });
  const uniRow = uni.data?.rows.find((r) => r.ticker === ticker.toUpperCase());
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const panel = params.get("panel") ?? "bridge";

  if (detail.isLoading)
    return (
      <div className="space-y-3" aria-busy="true">
        <Skeleton className="h-10 w-1/2 bg-zinc-800" />
        <Skeleton className="h-64 w-full bg-zinc-800" />
      </div>
    );

  if (detail.error) {
    const noDetail = String(detail.error).includes("NO_DETAIL");
    return (
      <div role="alert" className="rounded border border-zinc-700 bg-zinc-900 p-6">
        <h2 className="mb-1 text-lg font-semibold">
          {noDetail ? "No offline detail for this name" : "Failed to load company data"}
        </h2>
        <p className="text-sm text-zinc-400">
          {noDetail
            ? `${ticker.toUpperCase()} is in the universe results but its full fixture detail is not cached in this demo bundle.`
            : String(detail.error)}
        </p>
        {uniRow ? (
          <p className="mt-3 font-mono text-sm">
            Universe row: RiskScore {fmt(uniRow.risk_score, 3)} · det.{" "}
            {uniRow.determination ?? "—"}
          </p>
        ) : null}
      </div>
    );
  }

  const d = detail.data!;
  const m = d.measures;
  const prov = d.provenance;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-2">
        <h1 className="text-xl font-semibold text-zinc-50">{d.name ?? d.ticker}</h1>
        <span className="font-mono text-lg text-sky-300">{d.ticker}</span>
        <span className="text-sm text-zinc-400">
          {d.sector ?? "—"} · as-of {d.as_of ?? "—"} · vintage {d.meta.data_vintage}
        </span>
        <Badge
          variant="outline"
          className={
            d.applicability.model_applicable === false
              ? "border-fuchsia-500/60 bg-fuchsia-500/10 text-fuchsia-300"
              : "border-emerald-500/50 bg-emerald-500/10 text-emerald-300"
          }
        >
          {d.applicability.model_applicable === false
            ? `GATED: ${d.applicability.reason_code}`
            : "MODEL APPLICABLE"}
        </Badge>
        {d.rating.determination ? (
          <Badge variant="outline" className="border-zinc-600 text-zinc-300">
            {d.rating.determination}
          </Badge>
        ) : null}
      </header>

      {d.flags.length ? (
        <div className="flex flex-wrap gap-1.5" aria-label="flags">
          {d.flags.map((f) => (
            <FlagChip key={f.code} code={f.code} text={f.text} />
          ))}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-zinc-800 bg-zinc-900/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-300">
              Result — RiskScore first, letter last (a derived conversion)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-[13px]">
              <tbody>
                <Row
                  label="RiskScore (Eq. 5/12, drift-free)"
                  value={fmt(m.risk_score, 3)}
                  emphasis
                />
                <Row
                  label="Universe rank (safest = 1)"
                  value={uniRow ? fmt(uniRow.risk_rank, 0) : "—"}
                  emphasis
                />
                <Row
                  label="σ_A (annualized)"
                  value={pct(m.sigma_a)}
                  prov={
                    <Prov label="sigma">
                      Estimated by EM over the trailing 252 trading days; bootstrap 5–95%:{" "}
                      {pct(d.bootstrap.sigma_p05)}–{pct(d.bootstrap.sigma_p95)}.
                    </Prov>
                  }
                />
                <Row label="Asset value A" value={big(m.asset_value)} />
                <Row
                  label="η_A (drift)"
                  value={`${pct(m.eta_a)} (t = ${fmt(d.drift.t_stat, 2)})`}
                  prov={
                    <Prov label="drift">
                      Estimated over {fmt(d.drift.span_years, 1)}y; SE {pct(d.drift.se)};
                      regime {d.drift.regime}.
                    </Prov>
                  }
                />
                <Row label="Distance to Default" value={fmt(m.dd, 2)} />
                <Row label="EDF Φ(−DD)" value={pct(m.edf, 4)} />
                <Row label="PIT PD (1y)" value={pct(m.pit_pd, 4)} />
                <Row label="TTC PD" value={m.ttc_pd === null ? "—" : pct(m.ttc_pd, 4)} />
                <Row
                  label="S&P letter (interval)"
                  value={
                    <RatingCell
                      letter={d.rating.letter}
                      lo={d.rating.interval_low}
                      hi={d.rating.interval_high}
                      notches={d.rating.interval_notches}
                      basis={d.rating.basis}
                      determination={d.rating.determination}
                      bootstrapNote={
                        d.bootstrap.defective_fraction
                          ? `defective in ${pct(d.bootstrap.defective_fraction, 0)} of replicates`
                          : undefined
                      }
                    />
                  }
                />
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-300">Inputs & provenance</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-[13px]">
              <tbody>
                <Row
                  label="Statement used"
                  value={prov.statement_period_end ?? "—"}
                  prov={
                    <Prov label="statement">
                      Available-at {prov.statement_available_at ?? "—"} (
                      {prov.availability_method ?? "—"}); no row sees an unfiled statement.
                    </Prov>
                  }
                />
                <Row
                  label="Short-term debt field"
                  value={<span className="text-xs">{prov.st_debt_source ?? "—"}</span>}
                  prov={
                    <Prov label="st debt">
                      The matched balance-sheet line item.{" "}
                      {prov.debt_source_contradictory
                        ? "CONTRADICTORY: the source disagrees with itself (Total < LT)."
                        : "Source consistent."}
                    </Prov>
                  }
                />
                <Row
                  label="Long-term debt field"
                  value={<span className="text-xs">{prov.lt_debt_source ?? "—"}</span>}
                />
                <Row
                  label="Shares method"
                  value={<span className="text-xs">{prov.shares_method ?? "—"}</span>}
                  prov={
                    <Prov label="shares">
                      Reference date {prov.shares_reference_date ?? "—"} (constant-share
                      assumption, reference date stored per TIMING_PROTOCOL).
                    </Prov>
                  }
                />
                <Row label="Data retrieved" value={prov.cache_fetched_at ?? "—"} />
                <Row label="Producing commit" value={d.meta.git_sha} />
              </tbody>
            </table>
            <div className="mt-3">
              <div className="mb-1 text-xs text-zinc-500">
                EM-implied asset value ({d.em_path.length} pts, downsampled)
              </div>
              <Spark points={d.em_path} />
            </div>
          </CardContent>
        </Card>
      </div>

      <section aria-label="charts" className="space-y-2">
        <div role="tablist" aria-label="chart panels" className="flex gap-1.5">
          {(["bridge", "ladder", "plane"] as const).map((p) => (
            <button
              key={p}
              role="tab"
              aria-selected={panel === p}
              className={`rounded-md border px-3 py-1 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
                panel === p
                  ? "border-sky-500/60 bg-sky-500/10 text-sky-300"
                  : "border-zinc-700 bg-zinc-900 text-zinc-400 hover:text-zinc-200"
              }`}
              onClick={() => {
                const next = new URLSearchParams(params.toString());
                next.set("panel", p);
                router.replace(`${pathname}?${next.toString()}`, { scroll: false });
              }}
            >
              {p === "bridge" ? "rating bridge" : p === "ladder" ? "amplification ladder" : "µ–CCM plane"}
            </button>
          ))}
        </div>
        {panel === "bridge" ? (
          <RatingBridge d={d} />
        ) : panel === "ladder" ? (
          <AmplificationLadder
            company={d.amplification}
            companyTicker={d.ticker}
            median={val.data?.amplification_median ?? null}
          />
        ) : (
          <MuCcmPlane
            rows={(uni.data?.rows ?? []).filter((r) => r.ticker === d.ticker)}
            cloud={d.bootstrap_cloud}
            focusTicker={d.ticker}
          />
        )}
      </section>
    </div>
  );
}

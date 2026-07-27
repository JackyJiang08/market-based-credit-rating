"use client";

/** The universe view: filterable table + the three charts. Filter state
 *  lives in the URL (deep-linkable). */
import dynamic from "next/dynamic";

const TwoHistogram = dynamic(
  () => import("@/components/charts/universe-charts").then((m) => m.TwoHistogram),
  { ssr: false },
);
const RankScatter = dynamic(
  () => import("@/components/charts/universe-charts").then((m) => m.RankScatter),
  { ssr: false },
);
const NotchErrors = dynamic(
  () => import("@/components/charts/universe-charts").then((m) => m.NotchErrors),
  { ssr: false },
);
import { UniverseTable } from "@/components/universe-table";
import { Skeleton } from "@/components/ui/skeleton";
import { enumLabel } from "@/lib/labels";
import { loadUniverse, loadValidation } from "@/lib/data";
import type { Universe } from "@/lib/schemas";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

const DETS = ["SCALE_RESOLVED", "PINNED_AT_FLOOR", "PINNED_AT_SCALE_TOP",
  "MODEL_NOT_APPLICABLE", "NOT_RATED"];

export function UniverseView({ initial }: { initial?: Universe }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["universe"],
    queryFn: loadUniverse,
    initialData: initial,
  });
  const val = useQuery({ queryKey: ["validation"], queryFn: loadValidation });
  // window.location instead of useSearchParams: the hook forces the whole
  // subtree to client-render on static export, which blanked the table until
  // hydration (CLS 0.87, late LCP). Deep links still work via the effect.
  const [query, setQuery] = useState("");
  useEffect(() => setQuery(window.location.search), []);
  const params = useMemo(() => new URLSearchParams(query), [query]);

  const sector = params.get("sector") ?? "";
  const det = params.get("det") ?? "";
  const rated = params.get("rated") ?? "";

  const setParam = useCallback(
    (k: string, v: string) => {
      const next = new URLSearchParams(window.location.search);
      if (v) next.set(k, v);
      else next.delete(k);
      const qs = next.toString();
      window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
      setQuery(qs ? `?${qs}` : "");
    },
    [],
  );

  const rows = useMemo(() => {
    let out = data?.rows ?? [];
    if (sector) out = out.filter((r) => r.sector === sector);
    if (det) out = out.filter((r) => r.determination === det);
    if (rated === "yes") out = out.filter((r) => r.letter);
    if (rated === "no") out = out.filter((r) => !r.letter);
    return out;
  }, [data, sector, det, rated]);

  const sectors = useMemo(
    () => [...new Set((data?.rows ?? []).map((r) => r.sector).filter(Boolean))].sort() as string[],
    [data],
  );

  if (isLoading) return <Skeleton className="h-96 w-full bg-zinc-800" aria-busy="true" />;
  if (error)
    return (
      <div role="alert" className="rounded border border-rose-700 bg-rose-950/40 p-4 text-sm">
        {String(error)}
      </div>
    );

  const sel =
    "rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 " +
    "focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="universe filters">
        <select aria-label="sector filter" className={sel} value={sector}
          onChange={(e) => setParam("sector", e.target.value)}>
          <option value="">all sectors</option>
          {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select aria-label="determination filter" className={sel} value={det}
          onChange={(e) => setParam("det", e.target.value)}>
          <option value="">all determinations</option>
          {DETS.map((d) => <option key={d} value={d}>{enumLabel(d).label}</option>)}
        </select>
        <select aria-label="rated filter" className={sel} value={rated}
          onChange={(e) => setParam("rated", e.target.value)}>
          <option value="">rated + unrated</option>
          <option value="yes">rated only</option>
          <option value="no">no letter only</option>
        </select>
        <span className="font-mono text-xs text-zinc-400">{rows.length} names</span>
      </div>

      <UniverseTable rows={rows} />

      <div className="grid gap-4 lg:grid-cols-2">
        <section aria-label="model versus agency letters" className="min-h-[260px] space-y-1">
          <h2 className="text-sm font-medium text-zinc-300">
            Model letters vs sourced agency letters
          </h2>
          <TwoHistogram rows={rows} />
        </section>
        <div className="grid gap-4 sm:grid-cols-2">
          <section aria-label="rank scatter" className="min-h-[300px] space-y-1">
            <h2 className="text-sm font-medium text-zinc-300">Rank vs agency rank</h2>
            <RankScatter rows={rows} />
          </section>
          <section aria-label="notch errors" className="min-h-[220px] space-y-1">
            <h2 className="text-sm font-medium text-zinc-300">Letter notch error</h2>
            {val.data?.notch_errors ? (
              <NotchErrors errors={val.data.notch_errors.map((e) => e.notch_error)} />
            ) : (
              <Skeleton className="h-40 w-full bg-zinc-800" />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

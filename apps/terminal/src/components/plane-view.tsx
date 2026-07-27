"use client";

import { MuCcmPlane } from "@/components/charts/mu-ccm-plane";
import { Skeleton } from "@/components/ui/skeleton";
import { loadCompany, loadUniverse } from "@/lib/data";
import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** Universe-wide plane; ?focus=TICKER overlays that company's bootstrap
 *  cloud (deep-linkable). */
export function PlaneView() {
  const { data, isLoading } = useQuery({ queryKey: ["universe"], queryFn: loadUniverse });
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const focus = params.get("focus")?.toUpperCase() ?? "";
  const detail = useQuery({
    queryKey: ["company", focus],
    queryFn: () => loadCompany(focus),
    enabled: !!focus,
    retry: false,
  });

  if (isLoading || !data) return <Skeleton className="h-96 w-full bg-zinc-800" aria-busy="true" />;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label htmlFor="focus" className="text-xs text-zinc-400">
          overlay bootstrap cloud:
        </label>
        <select
          id="focus"
          className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          value={focus}
          onChange={(e) => {
            const next = new URLSearchParams(params.toString());
            if (e.target.value) next.set("focus", e.target.value);
            else next.delete("focus");
            router.replace(`${pathname}?${next.toString()}`, { scroll: false });
          }}
        >
          <option value="">none</option>
          {data.rows
            .filter((r) => r.detail_available && r.mu && r.ccm)
            .map((r) => (
              <option key={r.ticker} value={r.ticker}>
                {r.ticker}
              </option>
            ))}
        </select>
        {focus && detail.data ? (
          <span className="font-mono text-xs text-zinc-400">
            {detail.data.bootstrap_cloud.length} replicate points
          </span>
        ) : null}
      </div>
      <MuCcmPlane rows={data.rows} cloud={detail.data?.bootstrap_cloud} focusTicker={focus} />
    </div>
  );
}

"use client";

/** Universe-wide plane, static-first: the base SVG renders from build-time
 *  data (no JS required to see the chart); ?focus=TICKER overlays that
 *  company's bootstrap cloud. Focus state lives in window.location, not
 *  useSearchParams — a static export must not CSR-bail this page. */
import { MuCcmPlane } from "@/components/charts/mu-ccm-plane";
import { loadCompany, loadUniverse } from "@/lib/data";
import type { Universe } from "@/lib/schemas";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

type Preset = "" | "orcl" | "pinned" | "grid";

export function PlaneView({ initial }: { initial: Universe }) {
  const { data } = useQuery({
    queryKey: ["universe"],
    queryFn: loadUniverse,
    initialData: initial,
  });
  const [focus, setFocus] = useState("");
  const [preset, setPreset] = useState<Preset>("");

  useEffect(() => {
    const f = new URLSearchParams(window.location.search).get("focus");
    if (f) {
      setFocus(f.toUpperCase());
      if (f.toUpperCase() === "ORCL") setPreset("orcl");
    }
  }, []);

  const applyFocus = (t: string) => {
    setFocus(t);
    const next = new URLSearchParams(window.location.search);
    if (t) next.set("focus", t);
    else next.delete("focus");
    const q = next.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${q ? `?${q}` : ""}`);
  };

  const detail = useQuery({
    queryKey: ["company", focus],
    queryFn: () => loadCompany(focus),
    enabled: !!focus,
    retry: false,
  });

  const presets: { key: Preset; label: string }[] = [
    { key: "orcl", label: "ORCL cloud" },
    { key: "pinned", label: "pinned names" },
    { key: "grid", label: "grid box" },
  ];

  return (
    <div className="space-y-2">
      <p className="text-xs leading-relaxed text-zinc-400">
        How to read this: each point is a company placed by its expected default horizon µ
        (right = longer) and its consistency measure CCM; the diagonal lines are the seven
        published rating grades, so a firm&apos;s letter is just which band it falls in.
        Points below the AAA line sit beyond the scale&apos;s ceiling — that is the
        &ldquo;everything is AAA&rdquo; effect made visible.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-zinc-400">focus:</span>
        {presets.map((p) => (
          <button
            key={p.key}
            aria-pressed={preset === p.key}
            className={`rounded-md border px-2 py-1 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
              preset === p.key
                ? "border-sky-500/70 bg-sky-500/10 text-sky-300"
                : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-500"
            }`}
            onClick={() => {
              const next = preset === p.key ? "" : p.key;
              setPreset(next);
              applyFocus(next === "orcl" ? "ORCL" : "");
            }}
          >
            {p.label}
          </button>
        ))}
        <label htmlFor="focus" className="ml-2 text-xs text-zinc-400">
          overlay bootstrap cloud:
        </label>
        <select
          id="focus"
          className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          value={focus}
          onChange={(e) => {
            setPreset(e.target.value === "ORCL" ? "orcl" : "");
            applyFocus(e.target.value);
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
      <MuCcmPlane
        rows={data.rows}
        cloud={detail.data?.bootstrap_cloud}
        focusTicker={focus}
        highlight={preset === "pinned" || preset === "grid" ? preset : undefined}
      />
    </div>
  );
}

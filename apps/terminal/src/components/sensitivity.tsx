"use client";

/** Sensitivity playground: the published formulas, live.
 *
 * The lesson is labelled: every output says which sliders move it, and the
 * drift slider visibly NOT moving RiskScore is the point (Prop. 4.4.2).
 * A is held at its EM point estimate; D varies with the w slider — the
 * 7-notch convention finding as a lived experience.
 */
import { MuCcmPlane } from "@/components/charts/mu-ccm-plane";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { loadCompany, loadUniverse } from "@/lib/data";
import { fmt, pct } from "@/lib/format";
import { compute, type Inputs } from "@/lib/model";
import { useQuery } from "@tanstack/react-query";

import { useEffect, useMemo, useRef, useState } from "react";

const DEFAULTS: Inputs = {
  sigma: 0.3, assetValue: 2e11, stDebt: 1e10, ltDebt: 6e10, w: 0.5, eta: 0.08, T: 1,
};

function Slider({
  id, label, min, max, step, value, onChange, format,
}: {
  id: string; label: string; min: number; max: number; step: number;
  value: number; onChange: (v: number) => void; format: (v: number) => string;
}) {
  return (
    <label htmlFor={id} className="block space-y-1">
      <span className="flex justify-between text-xs text-zinc-400">
        <span>{label}</span>
        <span className="font-mono tabular-nums text-zinc-200">{format(value)}</span>
      </span>
      <input
        id={id} type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-sky-400"
        aria-label={label}
      />
    </label>
  );
}

function Out({
  label, value, movesWith, highlight, note,
}: {
  label: string; value: string; movesWith: string; highlight?: boolean; note?: string;
}) {
  return (
    <div className={`rounded-md border p-2.5 ${highlight ? "border-sky-500/50 bg-sky-500/5" : "border-zinc-800 bg-zinc-900/60"}`}>
      <div className="text-[11px] text-zinc-400">{label}</div>
      <div className="font-mono text-lg tabular-nums text-zinc-100" data-testid={`out-${label.split(" ")[0].toLowerCase()}`}>
        {value}
      </div>
      <div className="mt-1 text-[10px] text-zinc-400">
        moves with: <span className="text-zinc-300">{movesWith}</span>
        {note ? <span className="ml-1 text-sky-300/90">{note}</span> : null}
      </div>
    </div>
  );
}

export function Sensitivity() {
  const uni = useQuery({ queryKey: ["universe"], queryFn: loadUniverse });
  const [preset, setPreset] = useState("");
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("t");
    if (t) setPreset(t.toUpperCase());
  }, []);
  const detail = useQuery({
    queryKey: ["company", preset],
    queryFn: () => loadCompany(preset),
    enabled: !!preset,
    retry: false,
  });

  const [inp, setInp] = useState<Inputs>(DEFAULTS);
  const [etaTouched, setEtaTouched] = useState(false);
  const trail = useRef<{ mu: number; ccm: number }[]>([]);

  useEffect(() => {
    const d = detail.data;
    if (!d || d.measures.sigma_a === null) return;
    setInp({
      sigma: d.measures.sigma_a,
      assetValue: d.measures.asset_value ?? DEFAULTS.assetValue,
      stDebt: d.inputs.st_debt ?? 0,
      ltDebt: d.inputs.lt_debt ?? 0,
      w: 0.5,
      eta: d.measures.eta_a ?? 0.08,
      T: 1,
    });
    trail.current = [];
  }, [detail.data]);

  const out = useMemo(() => compute(inp), [inp]);
  if (out.mu && out.ccm) {
    const last = trail.current[trail.current.length - 1];
    if (!last || Math.abs(Math.log(last.mu / out.mu)) > 0.01 ||
        Math.abs(Math.log(last.ccm / out.ccm)) > 0.01) {
      trail.current = [...trail.current.slice(-59), { mu: out.mu, ccm: out.ccm }];
    }
  }

  const set = (k: keyof Inputs) => (v: number) => {
    if (k === "eta") setEtaTouched(true);
    setInp((p) => ({ ...p, [k]: v }));
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card className="border-zinc-800 bg-zinc-900/60">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-zinc-300">Inputs</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <label htmlFor="preset" className="block space-y-1 text-xs text-zinc-400">
            company preset (A, σ, η, debt from the fixture data)
            <select
              id="preset"
              className="mt-1 w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300"
              value={preset}
              onChange={(e) => {
                setPreset(e.target.value);
                const next = new URLSearchParams(window.location.search);
                if (e.target.value) next.set("t", e.target.value);
                else next.delete("t");
                const q = next.toString();
                window.history.replaceState(
                  null,
                  "",
                  `${window.location.pathname}${q ? `?${q}` : ""}`,
                );
              }}
            >
              <option value="">generic firm</option>
              {(uni.data?.rows ?? [])
                .filter((r) => r.detail_available && r.sigma_a)
                .map((r) => (
                  <option key={r.ticker} value={r.ticker}>{r.ticker}</option>
                ))}
            </select>
          </label>
          <Slider id="sigma" label="σ_A — asset volatility" min={0.05} max={1.2} step={0.005}
            value={inp.sigma} onChange={set("sigma")} format={(v) => pct(v, 1)} />
          <Slider id="w" label="w — long-term debt weight in D = ST + w·LT"
            min={0} max={1} step={0.05} value={inp.w} onChange={set("w")}
            format={(v) => fmt(v, 2)} />
          <Slider id="eta" label="η — asset drift (watch RiskScore NOT move)"
            min={-0.3} max={0.5} step={0.005} value={inp.eta} onChange={set("eta")}
            format={(v) => pct(v, 1)} />
          <Slider id="T" label="T — horizon (years)" min={0.25} max={3} step={0.25}
            value={inp.T} onChange={set("T")} format={(v) => fmt(v, 2)} />
          <p className="text-[10px] leading-relaxed text-zinc-400">
            A is held at its EM point estimate (re-estimating A per input is the
            pipeline&apos;s job, not the playground&apos;s). Letter via the analytical
            route on the published seven-grade scale — the licensed grids that
            notch it are not in this site.
          </p>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <Out label="RiskScore (Eq. 12)" value={out.riskScore ? fmt(out.riskScore, 3) : "—"}
            movesWith="σ, D (w)" highlight
            note={etaTouched ? "η does not enter — Prop. 4.4.2" : undefined} />
          <Out label="DD (Eq. 14)" value={out.dd ? fmt(out.dd, 2) : "—"}
            movesWith="σ, D, η, T" />
          <Out label="PIT PD (Eq. 13)" value={out.pitPd !== null ? pct(out.pitPd, 3) : "—"}
            movesWith="σ, D, η, T" />
          <Out label="Letter (analytical)" value={out.letter ?? (out.regime === "DEFECTIVE" ? "defective drift" : "—")}
            movesWith="everything — a derived conversion"
            note={out.atScaleTop ? "pinned at scale top" : undefined} />
        </div>
        <div className="text-xs text-zinc-400">
          D = {fmt(out.d / 1e9, 1)}B · ln(A/D) = {out.lnAD ? fmt(out.lnAD, 3) : "—"} ·
          regime {out.regime}
          {out.regime === "DEFECTIVE" ? " — µ/CCM/letter undefined (Prop. 4.4.1)" : ""}
        </div>
        <MuCcmPlane
          rows={
            out.mu && out.ccm
              ? [{
                  ticker: preset || "YOU", name: "playground point", sector: null,
                  risk_score: out.riskScore, risk_rank: null, sigma_a: inp.sigma,
                  mu: out.mu, ccm: out.ccm, dd: out.dd, letter: out.letter,
                  interval_low: null, interval_high: null, interval_notches: null,
                  basis: "ANALYTICAL", determination: null, firm_type: null,
                  applicability_reason: null, drift_t: null, weakly_identified: null,
                  taxonomy_category: null, taxonomy_detail: null, agency_sp: null,
                  agency_verified: null, detail_available: false,
                }]
              : []
          }
          cloud={trail.current}
          focusTicker={preset || "YOU"}
        />
      </div>
    </div>
  );
}

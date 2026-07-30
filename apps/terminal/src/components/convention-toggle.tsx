"use client";

/** Convention comparison for the names the team's reference implementation
 *  covers. DOCUMENTED stays the run of record; this block shows the same
 *  company under the reference convention, every value labeled, the
 *  abs-drift provenance rendered as a chip. Rendered only where a reference
 *  block exists in the exported data. */
import { FlagChip } from "@/components/flag-chips";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmt, pct } from "@/lib/format";
import type { CompanyDetail, ReferenceBlock } from "@/lib/schemas";
import { useState } from "react";

export function ConventionToggle({
  documented,
  reference,
}: {
  documented: CompanyDetail["measures"];
  reference: ReferenceBlock;
}) {
  const [active, setActive] = useState<"DOCUMENTED" | "REFERENCE">("DOCUMENTED");
  const isRef = active === "REFERENCE";
  const shown = isRef
    ? {
        risk_score: reference.risk_score,
        sigma_a: reference.sigma_a,
        eta_a: reference.eta_a,
        mu: reference.mu,
        ccm: reference.ccm,
      }
    : {
        risk_score: documented.risk_score,
        sigma_a: documented.sigma_a,
        eta_a: documented.eta_a,
        mu: documented.mu,
        ccm: documented.ccm,
      };

  const btn = (name: "DOCUMENTED" | "REFERENCE", label: string) => (
    <button
      aria-pressed={active === name}
      data-testid={`convention-${name.toLowerCase()}`}
      className={`rounded-md border px-2 py-1 text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
        active === name
          ? "border-sky-500/70 bg-sky-500/10 text-sky-300"
          : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-500"
      }`}
      onClick={() => setActive(name)}
    >
      {label}
    </button>
  );

  return (
    <Card className="border-zinc-800 bg-zinc-900/60" data-testid="convention-panel">
      <CardHeader className="pb-2">
        <CardTitle className="flex flex-wrap items-center gap-2 text-sm text-zinc-300">
          <span>Computation convention</span>
          {btn("DOCUMENTED", "Documented · run of record")}
          {btn("REFERENCE", "Reference")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-[13px]">
        <p className="text-xs leading-relaxed text-zinc-400">
          {isRef
            ? "Reference convention: µ divides by the raw η (no Ito adjustment), a negative η becomes |η| with a flag, and drift shares the 250-day volatility window. Same committed data vintage."
            : "Documented convention (the run of record everywhere on this site): µ divides by η − σ²/2, a negative drift is NOT_RATED, drift uses a ~5-year window."}
        </p>
        <table className="w-full tabular-nums">
          <tbody>
            {(
              [
                ["RiskScore", fmt(shown.risk_score, 3)],
                ["σ_A", pct(shown.sigma_a)],
                ["η_A", pct(shown.eta_a)],
                ["µ", fmt(shown.mu, 2)],
                ["CCM", fmt(shown.ccm, 4)],
              ] as const
            ).map(([k, v]) => (
              <tr key={k} className="border-b border-zinc-800/60 last:border-0">
                <td className="py-1 text-zinc-400">
                  {k}{" "}
                  <span className="text-[10px] text-zinc-400">
                    · {isRef ? "reference" : "documented"} convention
                  </span>
                </td>
                <td className="py-1 text-right font-mono text-zinc-100">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {isRef && reference.mu_uses_abs_drift ? (
          <div className="flex" data-testid="abs-drift-chip">
            <FlagChip code="MU_USES_ABS_DRIFT" />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

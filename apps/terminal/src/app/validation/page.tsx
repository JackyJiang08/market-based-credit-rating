import fs from "node:fs";
import path from "node:path";

export const metadata = { title: "Validation — Credit Rating Terminal" };

const REPO = "https://github.com/JackyJiang08/market-based-credit-rating";

type Disc = { stratum: string; n: number; spearman: number; spearman_ci05: number; spearman_ci95: number };

export default function ValidationPage() {
  const p = path.join(process.cwd(), "public", "data", "validation.json");
  const val = JSON.parse(fs.readFileSync(p, "utf-8"));
  const disc: Disc[] = val.discrimination ?? [];
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-zinc-50">Agency validation</h1>
        <p className="text-sm text-zinc-400">
          The model against sourced agency ratings — discrimination works, the letter
          conversion runs optimistic, and we publish both.{" "}
          <a className="underline underline-offset-2" href={`${REPO}/blob/main/docs/analysis/VALIDATION.md`}>
            Full study →
          </a>
        </p>
      </div>

      <section aria-label="discrimination">
        <h2 className="mb-2 text-sm font-medium text-zinc-300">
          Discrimination (Spearman ρ vs agency ordering, 90% bootstrap CI)
        </h2>
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-zinc-700 text-left text-zinc-400">
              <th className="px-2 py-1.5 font-medium">Stratum</th>
              <th className="px-2 py-1.5 text-right font-medium">n</th>
              <th className="px-2 py-1.5 text-right font-medium">ρ</th>
              <th className="px-2 py-1.5 text-right font-medium">90% CI</th>
            </tr>
          </thead>
          <tbody>
            {disc.map((d) => (
              <tr key={d.stratum} className="border-b border-zinc-800/70">
                <td className="px-2 py-1 text-zinc-300">{d.stratum}</td>
                <td className="px-2 py-1 text-right font-mono tabular-nums">{d.n}</td>
                <td className="px-2 py-1 text-right font-mono tabular-nums text-sky-300">
                  {d.spearman.toFixed(3)}
                </td>
                <td className="px-2 py-1 text-right font-mono tabular-nums text-zinc-400">
                  [{d.spearman_ci05.toFixed(2)}, {d.spearman_ci95.toFixed(2)}]
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {[
        ["letters_model_vs_agency.svg", "Model letters vs sourced agency letters — the letter conversion saturates at the top of the scale."],
        ["baseline_comparison.svg", "Baselines: plain distance-to-default ties the TiC RiskScore on discrimination; both beat leverage alone."],
        ["rank_scatter.svg", "RiskScore rank vs agency rank; scale-resolved names emphasized."],
        ["notch_errors.svg", "Letter notch error: median +5 notches optimistic."],
      ].map(([f, caption]) => (
        <figure key={f} className="overflow-x-auto rounded-lg border border-zinc-800 bg-[#fcfcfb] p-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`${base}/data/figures/${f}`} alt={caption} className="mx-auto max-w-full" />
          <figcaption className="px-2 pt-1 text-xs text-zinc-600">{caption}</figcaption>
        </figure>
      ))}
    </div>
  );
}

import Link from "next/link";

export const metadata = { title: "about — creditrating terminal" };

const REPO = "https://github.com/JackyJiang08/market-based-credit-rating";

export default function About() {
  return (
    <article className="prose-invert mx-auto max-w-2xl space-y-6 py-4 text-[15px] leading-relaxed text-zinc-300">
      <header>
        <h1 className="text-xl font-semibold text-zinc-50">About this terminal</h1>
      </header>

      <section className="space-y-2">
        <p>
          This is a working market-based credit-rating system: a KMV/Merton structural
          model estimated by EM over five years of equity data, converted to
          Time-Consistent (TiC) credit measures and an S&amp;P-equivalent letter, run
          across a 150-name universe chosen to include the hard cases — banks, ADRs,
          negative book equity, recent IPOs, genuinely distressed names. Everything on
          this site was computed offline from committed data and is reproducible from
          the repository with two commands.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-medium text-zinc-100">Finding one — the letter is the weak layer</h2>
        <p>
          The drift-free RiskScore inherits exactly the volatility&apos;s uncertainty
          (×2.00, the algebraic square) while the PD-based letter conversion amplifies
          it roughly <strong className="text-zinc-100">×4,073</strong> on the
          measured universe. The same letter also swings up to seven notches on an
          unargued debt-weight convention, and for deposit-funded banks no convention
          lands on the truth at all. The rank ordering underneath is robust to all of
          it — which is why this site shows RiskScore first and never renders a letter
          without its interval.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-medium text-zinc-100">Finding two — validated, honestly</h2>
        <p>
          Against sourced agency ratings the ordering discriminates well: Spearman ρ =
          0.79 overall and 0.73 restricted to the names where the scale genuinely
          resolved a letter, holding within every sector. Calibration is the failure
          mode: the letters run a median five notches optimistic, and plain
          distance-to-default ties the TiC RiskScore on discrimination — a result we
          report rather than bury. The full study, including where the model fails, is
          in the repository.
        </p>
      </section>

      <section className="space-y-1 text-sm">
        <h2 className="text-base font-medium text-zinc-100">Links</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li><a className="underline underline-offset-2" href={REPO}>Repository</a> — Apache-2.0, CI-green, offline-reproducible</li>
          <li><a className="underline underline-offset-2" href={`${REPO}/blob/main/docs/analysis/VALIDATION.md`}>Validation study</a> — discrimination, calibration, baselines</li>
          <li><a className="underline underline-offset-2" href={`${REPO}/tree/main/docs/deliverables`}>Frozen deliverable</a> — the workbook with its provenance README</li>
          <li><Link className="underline underline-offset-2" href="/sensitivity/">Sensitivity playground</Link> — the formulas, live in your browser</li>
        </ul>
      </section>

      <section className="space-y-1 text-xs text-zinc-400">
        <h2 className="text-sm font-medium text-zinc-300">Attribution</h2>
        <p>
          Independent implementation of the Time-Consistent (TiC) credit-rating
          methodology (Y. Yang); equation numbers are cited in the code. The
          methodology reference materials and conversion grids are licensed third-party
          material — not in the repository, not on this site. Fixture-backed demo;
          not investment advice.
        </p>
      </section>
    </article>
  );
}

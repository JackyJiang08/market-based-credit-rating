"""Regenerate docs/analysis/reference_reconciliation.md's numbers.

Runs the eight deliverable names under the DOCUMENTED convention and each
ablation step (window only; + raw-eta denominator; + abs = full REFERENCE),
pinned to the 2026-07-27 close, and prints the reconciliation and ablation
tables. The expected reference values are inlined constants sourced by
description only (team reference implementation, 2026-07-27 vintage); no
external file is read.

Usage (a refreshed cache directory keeps the committed fixtures untouched):

    MDT_CACHE_DIR=/tmp/refcache MDT_CACHE_REFRESH=1 \
        python docs/analysis/run_reference_reconciliation.py   # first run pulls
    MDT_CACHE_DIR=/tmp/refcache \
        python docs/analysis/run_reference_reconciliation.py   # reruns are offline
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "packages", "core"))

from creditrating.data import cache  # noqa: E402
from creditrating.data.pipeline import RunConfig, run  # noqa: E402
from creditrating.io import records  # noqa: E402
from creditrating.model.convention import DOCUMENTED, REFERENCE, Convention  # noqa: E402

NAMES = ["AMZN", "COST", "DELL", "INTU", "KHC", "KO", "ORCL", "PNC"]
AS_OF = "2026-07-27"

# Team reference implementation, 2026-07-27 vintage (displays at 4 dp).
# DELL/KHC/KO/PNC inputs were not provided and are deliberately absent.
REFERENCE_VALUES = {
    "AMZN": {"sigma": 0.2653, "eta": 0.1078, "mu": 16.9632, "ccm": 0.3569, "rs": 2.1038},
    "COST": {"sigma": 0.1882, "eta": 0.1623, "mu": 13.4993, "ccm": None, "rs": 0.7372},
    "INTU": {"sigma": None, "eta": -1.1008, "mu": 1.5477, "ccm": None, "rs": 8.6867},
    "ORCL": {"sigma": 0.4315, "eta": -0.3387, "mu": 2.7583, "ccm": 0.5883, "rs": 21.3296},
}

STEPS = [
    ("DOCUMENTED", DOCUMENTED),
    ("(a) window 250d", Convention("ABLATION_A", "ito_drift", "not_rated", 250, 250)),
    ("(b) + raw eta", Convention("ABLATION_B", "raw_eta", "not_rated", 250, 250)),
    ("(c) + abs", Convention("ABLATION_C", "raw_eta", "abs", 250, 250)),
    ("(d) + TL barrier = REFERENCE", REFERENCE),
]


def fmt(v, nd=4):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return f"{v:.{nd}f}"


def main() -> None:
    rows: dict[str, dict[str, dict]] = {}
    for label, conv in STEPS:
        companies = run(
            RunConfig(
                tickers=NAMES, convention=conv, as_of=AS_OF, workers=4, run_bootstrap=False
            )
        )
        for c in companies:
            r = records.credit_record(c)
            rows.setdefault(c.ticker, {})[label] = r

    print("\n## Reconciliation (ours under REFERENCE vs the reference values)\n")
    print(
        "| Name | sigma ours/ref | eta ours/ref | mu ours/ref | CCM ours/ref | RS ours/ref |"
    )
    print("|---|---|---|---|---|---|")
    for t in NAMES:
        r = rows[t]["(d) + TL barrier = REFERENCE"]
        ref = REFERENCE_VALUES.get(t)
        if ref is None:
            print(
                f"| {t} | {fmt(r['sigma_A'])} / n.p. | {fmt(r['eta_A'])} / n.p. "
                f"| {fmt(r['mu'])} / n.p. | {fmt(r['ccm'])} / n.p. "
                f"| {fmt(r['risk_score'])} / n.p. |"
            )
        else:
            print(
                f"| {t} | {fmt(r['sigma_A'])} / {fmt(ref['sigma'])} "
                f"| {fmt(r['eta_A'])} / {fmt(ref['eta'])} "
                f"| {fmt(r['mu'])} / {fmt(ref['mu'])} "
                f"| {fmt(r['ccm'])} / {fmt(ref['ccm'])} "
                f"| {fmt(r['risk_score'])} / {fmt(ref['rs'])} |"
            )

    print("\n## Ablation (mu / RiskScore at each step)\n")
    hdr = " | ".join(label for label, _ in STEPS)
    print(f"| Name | {hdr} | reference |")
    print("|---" * (len(STEPS) + 2) + "|")
    for t in NAMES:
        cells = []
        for label, _ in STEPS:
            r = rows[t][label]
            cells.append(f"{fmt(r['mu'], 2)} / {fmt(r['risk_score'], 3)}")
        ref = REFERENCE_VALUES.get(t)
        tail = f"{fmt(ref['mu'], 2)} / {fmt(ref['rs'], 3)}" if ref else "n.p."
        print(f"| {t} | {' | '.join(cells)} | {tail} |")

    print("\n## Barrier forensics (the named input difference)\n")
    print(
        "| Name | D ours (ST+0.5LT) | D* implied by reference ln(A/D) | Total Liabilities | TL / D* |"
    )
    print("|---|---|---|---|---|")
    companies = run(
        RunConfig(
            tickers=NAMES, convention=REFERENCE, as_of=AS_OF, workers=4, run_bootstrap=False
        )
    )
    by_t = {c.ticker: c for c in companies}
    for t, ref in REFERENCE_VALUES.items():
        c = by_t[t]
        E = float(c.panel["MarketCap_E"].dropna().iloc[-1])
        D = float(c.panel["DefaultPointDebt_D"].dropna().iloc[-1])
        ln_ref = ref["mu"] * abs(ref["eta"])
        d_star = E / (math.exp(ln_ref) - 1.0)  # solve ln((E+D*)/D*) = ln_ref
        stmts = cache.load_statements(t) or {}
        qb = stmts.get("q_balance")
        tl = None
        if qb is not None and "Total Liabilities Net Minority Interest" in qb.index:
            v = qb.loc["Total Liabilities Net Minority Interest", qb.columns[0]]
            tl = float(v) if v == v else None
        print(
            f"| {t} | {D:.3e} | {d_star:.3e} | " f"{tl:.3e} | {tl / d_star:.2f} |"
            if tl
            else f"| {t} | {D:.3e} | {d_star:.3e} | n/a | n/a |"
        )


if __name__ == "__main__":
    main()

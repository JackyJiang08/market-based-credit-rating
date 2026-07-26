"""Failure taxonomy and distributions for the expanded universe.

Re-runs the pipeline per company from the acquisition cache (offline once the
batch has populated ``data/cache/``) and classifies every name that does not
produce a rating:

    DATA_UNAVAILABLE      acquisition failed, or history too short for EM
    MODEL_NOT_APPLICABLE  an applicability gate fired (reason code attached)
    DEFECTIVE_DRIFT       Prop. 4.4.1 fails: eta - sigma^2/2 <= 0
    OFF_SCALE             (CCM, mu) outside the conversion grid -- no letter
    BUG                   anything else: an exception, or an unexplained blank

Also reports the distributions the 10-name universe was too small for:
sigma_A by sector, the drift-regime split, the determination split, and the
model-letter histogram against the approximate agency ratings recorded in
config/universe.yaml (indicative only, never a model input).

Writes docs/reconciliation/universe/{taxonomy,sigma_by_sector,determination,
rating_histogram}.csv and prints the report.

Usage:  python docs/reconciliation/universe_taxonomy.py [--workers 8]
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "packages", "core"))
sys.path.insert(0, ROOT)

from creditrating.data.pipeline import RunConfig, fetch_company   # noqa: E402
from creditrating.data import cache
from creditrating.data import providers as sources              # noqa: E402

OUT = os.path.join(HERE, "universe")


def classify(c, exc) -> tuple[str, str]:
    """(category, detail) for one company under the batch taxonomy."""
    if exc is not None:
        return "BUG", f"raised {type(exc).__name__}: {exc}"
    if c.data_status not in (None, "OK"):
        return "DATA_UNAVAILABLE", c.data_status
    # The applicability gates come before the sigma check: the currency gate
    # deliberately leaves sigma_A unset (the measures would be unit-corrupt).
    if c.model_applicable is False:
        return "MODEL_NOT_APPLICABLE", c.applicability_reason or "?"
    if c.sigma_A is None:
        detail = c.em_error or "EM/measures did not run (no recorded reason)"
        low = detail.lower()
        if "observation" in low or "short" in low or "empty" in low \
                or "fewer" in low or "no usable" in low:
            return "DATA_UNAVAILABLE", f"INSUFFICIENT_HISTORY ({detail})"
        return "BUG", detail
    if c.model_applicable is False:
        return "MODEL_NOT_APPLICABLE", c.applicability_reason or "?"
    if c.drift_regime == "DEFECTIVE":
        return "DEFECTIVE_DRIFT", f"drift t={c.drift_t_stat:.2f}"
    if c.sp_rating:
        return "RATED", c.sp_rating
    if c.rating_basis == "OFF_GRID":
        return "OFF_SCALE", f"OFF_GRID (CCM={c.ccm:.4g}, mu={c.mu:.4g})"
    return "BUG", (f"no letter and no explanation (basis={c.rating_basis}, "
                   f"determination={c.rating_determination})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    import yaml
    with open(os.path.join(ROOT, "config", "universe.yaml")) as fh:
        entries = yaml.safe_load(fh)["companies"]
    agency = {e["ticker"]: e.get("agency") for e in entries}
    tickers = list(agency)

    cfg = RunConfig(tickers=tickers, run_bootstrap=False)
    rates = cache.load_rates()
    if rates is None:
        rates = sources.fetch_rates(cfg.years)
        cache.save_rates(rates)

    def one(t):
        try:
            return t, fetch_company(t, cfg, rates), None
        except Exception as exc:  # noqa: BLE001 - the taxonomy needs the raiser
            return t, None, exc

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(one, tickers))

    rows = []
    for t, c, exc in results:
        cat, detail = classify(c, exc)
        rows.append({
            "symbol": t,
            "category": cat,
            "detail": detail,
            "sector": getattr(c, "sector", None) if c else None,
            "firm_type": getattr(c, "firm_type", None) if c else None,
            "sigma_A": getattr(c, "sigma_A", None) if c else None,
            "drift_regime": getattr(c, "drift_regime", None) if c else None,
            "determination": getattr(c, "rating_determination", None) if c else None,
            "model_letter": getattr(c, "sp_rating", None) if c else None,
            "agency_approx": agency.get(t),
            "financial_currency": (getattr(c, "financial_currency", None)
                                   if c else None),
            "price_currency": getattr(c, "currency", None) if c else None,
        })
    df = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, "taxonomy.csv"), index=False)

    print("\n=== FAILURE TAXONOMY (n=%d) ===" % len(df))
    print(df["category"].value_counts().to_string())
    for cat in ("BUG", "DATA_UNAVAILABLE", "MODEL_NOT_APPLICABLE",
                "DEFECTIVE_DRIFT", "OFF_SCALE"):
        sub = df[df["category"] == cat]
        if not sub.empty:
            print(f"\n--- {cat} ---")
            print(sub[["symbol", "detail"]].to_string(index=False))

    ok = df[df["sigma_A"].notna()]
    sig = (ok.groupby("sector")["sigma_A"]
             .agg(["count", "median", "min", "max"])
             .sort_values("median", ascending=False))
    sig.to_csv(os.path.join(OUT, "sigma_by_sector.csv"))
    print("\n=== sigma_A BY SECTOR ===")
    print(sig.to_string(float_format=lambda x: f"{x:.3f}"))

    print("\n=== DRIFT REGIME (names with estimates) ===")
    print(ok["drift_regime"].value_counts().to_string())

    det = df["determination"].value_counts(dropna=False)
    det.to_csv(os.path.join(OUT, "determination.csv"))
    print("\n=== DETERMINATION ===")
    print(det.to_string())

    hist = pd.DataFrame({
        "model": df["model_letter"].value_counts(),
        "agency_approx": df["agency_approx"].value_counts(),
    }).fillna(0).astype(int)
    hist.to_csv(os.path.join(OUT, "rating_histogram.csv"))
    print("\n=== MODEL LETTERS vs APPROXIMATE AGENCY ===")
    print(hist.to_string())


if __name__ == "__main__":
    main()

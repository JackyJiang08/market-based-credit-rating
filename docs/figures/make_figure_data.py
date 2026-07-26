"""Regenerate the data behind docs/figures/*.svg.

Runs the live pipeline (network) and a 2,000-replicate moving-block bootstrap
per company -- the study-of-record configuration (seed 20260726) -- and writes
the figure inputs to docs/figures/data/:

  amplification.csv       median relative 5-95 interval width per quantity
  rank_distribution.csv   fraction of replicates in which company i holds rank r
  rank_stability.csv      Kendall's tau of each replicate's ordering vs the point
  rating_intervals.csv    copied view of history/14: point letter + interval

The convention-sweep letters (convention_sweep_letters.csv) are NOT produced
here: they are the recorded output of docs/reconciliation/convention_sweep.py
(run 2026-07-26) and change only when that sweep is re-run.

Requires local/ (the TTC conversion tables) and network access. The committed
CSVs are the record; this script is how they regenerate when the data vintage
moves.

Usage:  python docs/figures/make_figure_data.py [--replicates 2000]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from data_cleaning.workflow import RunConfig, fetch_company          # noqa: E402
from raw_data_architecture import sources                            # noqa: E402
from signal_construction import bootstrap as bs                      # noqa: E402
from signal_construction import config as sig_config                 # noqa: E402
from signal_construction import conversion, em                       # noqa: E402

DATA_DIR = os.path.join(HERE, "data")
QUANTITIES = ("sigma_A", "risk_score", "dd", "ttc_pd", "pit_pd")


def _bootstrap_company(ticker: str, cfg: RunConfig, rates, tables, n: int):
    """Fetch one company and return its BootstrapResult (study-of-record config)."""
    c = fetch_company(ticker, cfg, rates)
    if c is None or c.panel is None or c.panel.empty:
        raise RuntimeError(f"{ticker}: no panel")
    window = c.panel.tail(sig_config.DRIFT_WINDOW_DAYS)
    res = em.estimate(window["MarketCap_E"], window["DefaultPointDebt_D"],
                      window["RiskFree_R"])
    u = np.diff(np.log(res.asset_values.to_numpy()))
    return bs.run(ticker, u, res.asset_last, res.debt_last, tables,
                  n_replicates=n, seed=bs.DEFAULT_SEED)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replicates", type=int, default=bs.DEFAULT_REPLICATES)
    args = ap.parse_args()

    import yaml
    with open(os.path.join(ROOT, "config", "companies.yaml")) as fh:
        tickers = [str(t).strip() for t in yaml.safe_load(fh)["companies"]]

    tables = conversion.load_tables()          # raises without local/ -- intended
    cfg = RunConfig(tickers=tickers, run_bootstrap=False)
    rates = sources.fetch_rates(cfg.years)

    results = {}
    for t in tickers:
        results[t] = _bootstrap_company(t, cfg, rates, tables, args.replicates)
        print(f"  {t}: {results[t].n_replicates} replicates")

    os.makedirs(DATA_DIR, exist_ok=True)

    # --- amplification ladder: median (across companies) relative width -----
    rows = [{"quantity": q,
             "median_relative_width": float(np.nanmedian(
                 [results[t].relative_width(q) for t in tickers]))}
            for q in QUANTITIES]
    pd.DataFrame(rows).to_csv(os.path.join(DATA_DIR, "amplification.csv"),
                              index=False)

    # --- rank distribution over replicates (RiskScore, ascending = safest) --
    rs = np.column_stack([results[t].risk_score for t in tickers])
    finite = np.isfinite(rs).all(axis=1)
    rs = rs[finite]
    order = np.argsort(np.argsort(rs, axis=1), axis=1) + 1   # rank per replicate
    frac = {t: np.bincount(order[:, i], minlength=len(tickers) + 1)[1:] / len(rs)
            for i, t in enumerate(tickers)}
    point = {t: r for r, t in enumerate(
        sorted(tickers, key=lambda t: results[t].quantiles("risk_score")[0.5]), 1)}
    recs = [{"symbol": t, "point_rank": point[t], "rank": r + 1,
             "fraction": float(frac[t][r])}
            for t in tickers for r in range(len(tickers))]
    pd.DataFrame(recs).to_csv(os.path.join(DATA_DIR, "rank_distribution.csv"),
                              index=False)

    # --- ordering stability: Kendall's tau per replicate vs the point order -
    from scipy.stats import kendalltau
    point_vec = np.array([point[t] for t in tickers])
    taus = np.array([kendalltau(point_vec, order[i]).correlation
                     for i in range(len(order))])
    pd.DataFrame([{
        "n_replicates_used": len(order),
        "tau_median": float(np.median(taus)),
        "tau_p05": float(np.quantile(taus, 0.05)),
        "tau_min": float(np.min(taus)),
        "share_tau_ge_0.8": float(np.mean(taus >= 0.8)),
    }]).to_csv(os.path.join(DATA_DIR, "rank_stability.csv"), index=False)

    # --- rating intervals: a stable view of the current history capture -----
    hist = pd.read_csv(os.path.join(
        ROOT, "docs", "reconciliation", "history",
        "14_after_dell_market_gate.csv"))
    hist[["Symbol", "TiC Risk Score", "SP Rating", "Rating Determination",
          "Rating Interval Low", "Rating Interval High",
          "Rating Interval Notches"]].to_csv(
        os.path.join(DATA_DIR, "rating_intervals.csv"), index=False)

    print(f"wrote {DATA_DIR}/")


if __name__ == "__main__":
    main()

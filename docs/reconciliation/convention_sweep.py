"""Convention uncertainty: how much of the rating is a modelling choice?

`docs/UNCERTAINTY.md` reports *parameter* uncertainty -- the sampling error in
`sigma_A` and the drift, propagated by bootstrap. It explicitly holds `A_0` and
`D` fixed, on the grounds that they are observations.

`D` is not an observation. It is `1.0 x ST + 0.5 x LT`, and the 0.5 is a
convention, not a measurement. So is the choice of long-term debt field, and so
is which statement vintage a valuation date sees. This script measures what
those choices are worth, on the same scale as the bootstrap interval, so the two
can be compared directly.

Sweeps
------
1. **Long-term debt weight** over {0, 0.25, 0.5, 0.75, 1.0}. Zero treats only
   short-term debt as the barrier; one treats all debt as due. The deck's 0.5 is
   the midpoint of a range nobody has justified from data.
2. **Statement vintage**: the latest statement the valuation date may see, versus
   the one before it. Not a look-ahead question -- both are legitimately
   available -- but a question of how much a quarter of staleness is worth.

Usage:  python docs/reconciliation/convention_sweep.py
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from data_cleaning import alignment                       # noqa: E402
from data_cleaning import config as clean_config          # noqa: E402
from signal_construction import bootstrap as bs           # noqa: E402
from signal_construction import config as sig_config      # noqa: E402
from signal_construction import conversion, em, measures  # noqa: E402

TICKERS = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT", "INTU", "AMZN", "T", "KHC"]
LT_WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]
OUT_CSV = os.path.join(HERE, "convention_sweep.csv")


def _panel(ticker: str) -> pd.DataFrame:
    path = os.path.join(clean_config.CLEAN_DATA_DIR, ticker, "aligned_panel.csv")
    return pd.read_csv(path, index_col=0, parse_dates=True).sort_index()


def rate_with(panel: pd.DataFrame, debt: pd.Series, tables) -> dict:
    """Run EM -> measures -> conversion on a given default-point series."""
    w = panel.tail(sig_config.DRIFT_WINDOW_DAYS)
    equity = alignment.total_return_close(w["Close"], w["Dividends"]) * w["Shares"]
    d = debt.reindex(w.index)
    out = {"letter": None, "notch": np.nan, "risk_score": np.nan,
           "regime": None, "D": float("nan")}
    try:
        res = em.estimate(equity, d, w["RiskFree_R"])
        m = measures.compute(res.sigma_A, res.asset_last, res.debt_last, res.eta_A)
    except Exception as exc:                               # noqa: BLE001
        # D = 0 is the informative failure: at w = 0 a company whose
        # short-term debt is zero has no barrier at all, so A > D > 0 fails.
        # For PNC that is not a quirk -- its ST = 0 is an artifact of the
        # missing current-debt row (#16), so its entire default point is the
        # long-term weight.
        last_d = float(d.dropna().iloc[-1]) if d.notna().any() else float("nan")
        out["letter"] = "D=0" if last_d == 0 else f"ERR:{type(exc).__name__}"
        return out

    out["D"] = res.debt_last
    out["risk_score"] = m.risk_score
    out["regime"] = m.regime.value
    if m.regime is measures.DriftRegime.DEFECTIVE:
        out["letter"] = "NOT_RATED"
        return out

    look = conversion.ttc_pd(tables, m.ccm, m.mu, pit_pd=m.pit_pd)
    if not np.isfinite(look.value):
        out["letter"] = look.basis.value
        return out
    label = conversion.sp_rating(tables, look.value)
    out["letter"] = label
    if label in tables.sp_labels:
        out["notch"] = tables.sp_labels.index(label)
    return out


def previous_vintage_debt(panel: pd.DataFrame) -> pd.Series | None:
    """The default point one statement older than the one each row actually saw.

    Shifts each row back to the previous distinct `StatementPeriodEnd`, so the
    whole panel is re-run one vintage stale. Returns None when the panel does not
    carry the audit column or has only one statement.
    """
    if "StatementPeriodEnd" not in panel.columns:
        return None
    pe = pd.to_datetime(panel["StatementPeriodEnd"], errors="coerce")
    known = sorted({d for d in pe.dropna().unique()})
    if len(known) < 2:
        return None
    prev_of = {known[i]: known[i - 1] for i in range(1, len(known))}
    prev_of[known[0]] = pd.NaT

    st_by, lt_by = {}, {}
    for d in known:
        rows = panel[pe == d]
        st_by[d] = rows["ShortTermDebt"].dropna().iloc[-1] if rows["ShortTermDebt"].notna().any() else np.nan
        lt_by[d] = rows["LongTermDebt"].dropna().iloc[-1] if rows["LongTermDebt"].notna().any() else np.nan

    st = pe.map(lambda d: st_by.get(prev_of.get(d), np.nan) if pd.notna(d) else np.nan)
    lt = pe.map(lambda d: lt_by.get(prev_of.get(d), np.nan) if pd.notna(d) else np.nan)
    return (clean_config.SHORT_TERM_DEBT_WEIGHT * st.fillna(0)
            + clean_config.LONG_TERM_DEBT_WEIGHT * lt.fillna(0)).where(
                st.notna() | lt.notna())


def main() -> int:
    tables = conversion.load_tables()
    rows = []

    print("=" * 104)
    print("CONVENTION UNCERTAINTY vs PARAMETER UNCERTAINTY")
    print("=" * 104)
    header = (f"{'tk':6s} " + " ".join(f"{'w=' + str(w):>10s}" for w in LT_WEIGHTS)
              + f" {'prev vint':>10s} | {'conv span':>10s} | {'boot span':>10s}")
    print(header)

    for t in TICKERS:
        try:
            panel = _panel(t)
        except FileNotFoundError:
            continue

        letters, notches = [], []
        for w in LT_WEIGHTS:
            d = (clean_config.SHORT_TERM_DEBT_WEIGHT * panel["ShortTermDebt"].fillna(0)
                 + w * panel["LongTermDebt"].fillna(0))
            d = d.where(panel["ShortTermDebt"].notna() | panel["LongTermDebt"].notna())
            r = rate_with(panel, d, tables)
            letters.append(r["letter"])
            notches.append(r["notch"])
            rows.append({"ticker": t, "sweep": "lt_weight", "value": w, **r})

        prev = previous_vintage_debt(panel)
        if prev is not None:
            rv = rate_with(panel, prev, tables)
            rows.append({"ticker": t, "sweep": "prev_vintage", "value": -1, **rv})
            prev_letter = rv["letter"]
            prev_notch = rv["notch"]
        else:
            prev_letter, prev_notch = "n/a", np.nan

        # Convention span: notches covered by every variant that produced a letter.
        all_n = [n for n in notches + [prev_notch] if np.isfinite(n)]
        conv_span = int(max(all_n) - min(all_n) + 1) if all_n else 0

        # Parameter span from the bootstrap, on the shipped convention.
        w = panel.tail(sig_config.DRIFT_WINDOW_DAYS)
        eq = alignment.total_return_close(w["Close"], w["Dividends"]) * w["Shares"]
        try:
            res = em.estimate(eq, w["DefaultPointDebt_D"], w["RiskFree_R"])
            u = np.diff(np.log(res.asset_values.to_numpy()))
            b = bs.run(t, u, res.asset_last, res.debt_last, tables, n_replicates=1000)
            _, _, boot_span = b.notch_interval()
        except Exception:                                   # noqa: BLE001
            boot_span = 0

        rows[-1]["conv_span"] = conv_span
        print(f"{t:6s} " + " ".join(f"{str(x):>10s}" for x in letters)
              + f" {str(prev_letter):>10s} | {conv_span:10d} | {boot_span:10d}")

    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    print(f"\nwrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

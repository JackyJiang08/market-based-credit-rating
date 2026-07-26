"""2x2 crossover study: our submission vs. a peer implementation of the same spec.

Read-only with respect to the model. This script imports the pipeline's Layer-3
modules and re-runs them over different *inputs* and *conventions*; it does not
modify anything under the four workflow layers.

The four cells
--------------
The study asks how much of the output gap between the two workbooks is explained
by inputs alone, by reporting/field conventions alone, and by genuine
implementation difference.

    A  OURS                    our inputs      + our conventions   (recomputed)
    B  OUR_MODEL_THEIR_INPUTS  their inputs    + our conventions   (recomputed)
    C  THEIR_CONV_OUR_INPUTS   our inputs      + their conventions (recomputed)
    D  THEIRS_REPORTED         their inputs    + their model       (read from file)

Cell D is *read*, not recomputed: the peer published a workbook, not code, so
"their model" is not executable here. The decomposition therefore reads:

    input effect       = B - A     (vintage + field selection, our model held fixed)
    convention effect  = C - A     (their debt-field convention, our inputs held fixed)
    residual           = D - B     (what inputs and conventions do NOT explain)

The residual is the only term that can contain a genuine implementation
difference, and it is an upper bound on one: it also absorbs any input we could
not replicate (see PRICE SERIES below).

PRICE SERIES
------------
The peer workbook publishes a single last price, not the daily series its EM was
fitted on. Every cell here is therefore fitted on OUR cached price panel,
truncated to the relevant as-of date. Cell B is "their balance-sheet and share
inputs on our price history", not a full replication of their input set.

Inputs
------
  docs/reconciliation/other_answer.xlsx   peer workbook, `Asset` sheet
  data_cleaning/data/<T>/aligned_panel.csv        our cached model panel
  raw_data_architecture/data/<T>/quarterly_balance_sheet.csv

All three input trees are git-ignored (proprietary or regenerable), so this
script runs only where those caches exist. Results are written to
docs/reconciliation/crossover_results.csv and mirrored as tables in REPORT.md.

Usage:  python docs/reconciliation/crossover.py
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "packages", "core"))
sys.path.insert(0, ROOT)

from creditrating.data import cleaning_config as clean_config          # noqa: E402
from creditrating.model import config as sig_config      # noqa: E402
from creditrating.model import conversion, em
from creditrating.model import tic as measures  # noqa: E402

PEER_XLSX = os.path.join(HERE, "other_answer.xlsx")
OUT_CSV = os.path.join(HERE, "crossover_results.csv")

TICKERS = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT", "INTU", "AMZN", "T", "KHC"]

# The peer's as-of price date, read from their `Last Date` column.
PEER_AS_OF = "2026-06-30"

# Third source: figures transcribed by hand from the screenshot (A in USD bn).
SCREENSHOT = {
    "COST": (407.6, 0.2222, 22.43), "KO":   (377.0, 0.1508, 18.92),
    "DELL": (464.8, 0.3092, 5.42),  "ORCL": (455.5, 0.3774, 6.25),
    "PNC":  (132.8, 0.1810, 7.77),  "WMT":  (920.9, 0.4613, 7.34),
    "INTU": (78.1, 0.3639, 8.50),   "AMZN": (2714.6, 1.2474, 2.47),
    "T":    (194.6, 0.4312, 3.01),  "KHC":  (37.8, 0.2862, 5.04),
}


# --------------------------------------------------------------------------- #
# Input loading
# --------------------------------------------------------------------------- #
def load_panel(ticker: str) -> pd.DataFrame:
    """Our cached aligned panel (Layer 2 output)."""
    path = os.path.join(clean_config.CLEAN_DATA_DIR, ticker, "aligned_panel.csv")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df.sort_index()


def load_raw_balance(ticker: str) -> pd.DataFrame:
    """Our cached quarterly balance sheet (Layer 1 output), as reported by the source."""
    path = os.path.join(clean_config.RAW_DATA_DIR, ticker, "quarterly_balance_sheet.csv")
    return pd.read_csv(path, index_col=0)


def load_peer() -> pd.DataFrame:
    """The peer `Asset` sheet, keyed by ticker."""
    df = pd.read_excel(PEER_XLSX, sheet_name="Asset")
    df.columns = [str(c).strip() for c in df.columns]
    return df.set_index("Symbol")


def peer_inputs(peer: pd.DataFrame, ticker: str) -> dict:
    """The peer's declared model inputs for one company."""
    row = peer.loc[ticker]
    st = float(row["Debt/Short Term"] or 0.0)
    lt = float(row["Debt/Long Term"] or 0.0)
    return {
        "shares": float(row["Shares Outstanding"]),
        "st_debt": st,
        "lt_debt": lt,
        # Their `Total Debt` column already carries the 50%-adjusted default point.
        "D": st + clean_config.LONG_TERM_DEBT_WEIGHT * lt,
        "rate": float(row["Interest Rate"]),
        "last_price": float(row["Last Price"]),
        "stmt_date": str(row["Last Statement Date"])[:10],
        "as_of": str(row["Last Date"])[:10],
    }


def peer_outputs(peer: pd.DataFrame, ticker: str) -> dict:
    """The peer's reported results for one company."""
    row = peer.loc[ticker]

    def g(col):
        # np.int64 is not a Python int on 64-bit builds, so coerce rather than isinstance.
        return pd.to_numeric(row.get(col), errors="coerce")

    drift = g("R")
    return {
        "sigma_A": g("σ"), "asset": g("A"), "eta_A": g("η"), "drift": drift,
        "ccm": g("CCM"), "mu": g("µ"), "risk_score": g("TiC Risk Score"),
        "dd": g("DD"), "edf": g("EDF"), "pit_pd": g("PIT PD"),
        "ttc_pd": g("TTC PD"), "sp_rating": row.get("SP Rating"),
        "neg_drift": bool(drift < 0) if pd.notna(drift) else None,
        # Their grid coverage, judged against the same axes our lookup uses.
        "off_grid": None,
    }


def plain_long_term_debt(ticker: str, stmt_date: str | None = None) -> float | None:
    """`Long Term Debt` as reported, i.e. the peer's field convention.

    Our pipeline prefers `Long Term Debt And Capital Lease Obligation`
    (data_cleaning/config.py BALANCE_SHEET_MAP); this reads the plain row that
    excludes capitalized leases.
    """
    bal = load_raw_balance(ticker)
    if "Long Term Debt" not in bal.index:
        return None
    row = bal.loc["Long Term Debt"].dropna()
    if row.empty:
        return None
    if stmt_date and stmt_date in row.index:
        return float(row[stmt_date])
    return float(row.iloc[0])


# --------------------------------------------------------------------------- #
# One model run
# --------------------------------------------------------------------------- #
def run_model(equity: pd.Series, debt: pd.Series, rate: pd.Series) -> dict:
    """Our EM + measures + conversion over a prepared window. Never raises."""
    out = {k: np.nan for k in
           ("sigma_A", "asset", "eta_A", "drift", "ccm", "mu", "risk_score",
            "dd", "edf", "pit_pd", "ttc_pd")}
    out["sp_rating"] = None
    out["off_grid"] = None
    out["neg_drift"] = None
    try:
        res = em.estimate(equity, debt, rate)
    except Exception as exc:                                   # noqa: BLE001
        out["error"] = f"EM: {exc}"
        return out
    try:
        m = measures.compute(res.sigma_A, res.asset_last, res.debt_last, res.eta_A)
    except Exception as exc:                                   # noqa: BLE001
        out["error"] = f"measures: {exc}"
        out["sigma_A"], out["eta_A"], out["asset"] = res.sigma_A, res.eta_A, res.asset_last
        return out

    out.update(sigma_A=m.sigma_A, asset=m.asset, eta_A=m.eta_A, drift=m.drift,
               ccm=m.ccm, mu=m.mu, risk_score=m.risk_score, dd=m.dd, edf=m.edf,
               pit_pd=m.pit_pd, neg_drift=bool(m.drift < 0), error="")

    # Conversion needs the proprietary grid; absent it, the row stays partial.
    try:
        tables = conversion.load_tables()
        ttc = conversion.ttc_pd(tables, m.ccm, m.mu)
        out["ttc_pd"] = ttc.value
        out["sp_rating"] = conversion.sp_rating(tables, ttc.value)
        out["off_grid"] = bool(ttc.off_grid)
        out["outlook"] = conversion.outlook(m.pit_pd, ttc.value)
        out["ccm_axis_lo"], out["ccm_axis_hi"] = float(tables.ccm_axis.min()), float(tables.ccm_axis.max())
        out["mu_axis_lo"], out["mu_axis_hi"] = float(tables.mu_axis.min()), float(tables.mu_axis.max())
    except FileNotFoundError:
        out["error"] = (out.get("error") or "") + " conversion: grid absent"
    return out


def window_for(panel: pd.DataFrame, as_of: str | None) -> pd.DataFrame:
    """Trailing EM window ending at `as_of` (inclusive), matching workflow.run."""
    p = panel if as_of is None else panel.loc[:as_of]
    return p.tail(sig_config.EM_WINDOW_DAYS)


# --------------------------------------------------------------------------- #
# The four cells
# --------------------------------------------------------------------------- #
def cell_ours(panel: pd.DataFrame) -> dict:
    """A: our inputs, our conventions — reproduces the submission workbook."""
    w = window_for(panel, None)
    return run_model(w["MarketCap_E"], w["DefaultPointDebt_D"], w["RiskFree_R"])


def cell_our_model_their_inputs(panel: pd.DataFrame, pin: dict) -> dict:
    """B: their shares / debt / rate / as-of date, our model."""
    w = window_for(panel, pin["as_of"])
    if w.empty:
        return {"error": "no panel rows at peer as-of date"}
    equity = w["DivAddBackClose"] * pin["shares"]
    debt = pd.Series(pin["D"], index=w.index)
    rate = pd.Series(pin["rate"], index=w.index)
    return run_model(equity, debt, rate)


def cell_their_conv_our_inputs(panel: pd.DataFrame, ticker: str,
                               stmt_date: str | None) -> dict:
    """C: our inputs and as-of date, their debt-field convention.

    The one convention that is unambiguously recoverable from the peer workbook
    is the long-term debt field: they report plain `Long Term Debt`, we report
    `Long Term Debt And Capital Lease Obligation`. Everything else is held at
    our values.
    """
    w = window_for(panel, None).copy()
    plain_lt = plain_long_term_debt(ticker, stmt_date)
    if plain_lt is None:
        return {"error": "no plain `Long Term Debt` row in source"}
    d = (clean_config.SHORT_TERM_DEBT_WEIGHT * w["ShortTermDebt"].fillna(0)
         + clean_config.LONG_TERM_DEBT_WEIGHT * plain_lt)
    return run_model(w["MarketCap_E"], d, w["RiskFree_R"])


# --------------------------------------------------------------------------- #
def main() -> int:
    if not os.path.exists(PEER_XLSX):
        print(f"missing peer workbook: {PEER_XLSX}", file=sys.stderr)
        return 2
    peer = load_peer()

    rows = []
    for t in TICKERS:
        try:
            panel = load_panel(t)
        except FileNotFoundError:
            print(f"  {t}: no cached panel — run `python -m mdt batch` first", file=sys.stderr)
            continue
        pin = peer_inputs(peer, t)

        cells = {
            "A_ours": cell_ours(panel),
            "B_our_model_their_inputs": cell_our_model_their_inputs(panel, pin),
            "C_their_conv_our_inputs": cell_their_conv_our_inputs(panel, t, pin["stmt_date"]),
            "D_theirs_reported": peer_outputs(peer, t),
        }
        for name, res in cells.items():
            rows.append({
                "ticker": t, "cell": name,
                "as_of": pin["as_of"] if name == "B_our_model_their_inputs"
                         else (panel.index[-1].strftime("%Y-%m-%d")
                               if name.startswith(("A_", "C_")) else pin["as_of"]),
                "D_used": (pin["D"] if name == "B_our_model_their_inputs"
                           else float(panel["DefaultPointDebt_D"].iloc[-1])
                           if name == "A_ours" else np.nan),
                **{k: res.get(k) for k in
                   ("sigma_A", "asset", "eta_A", "drift", "ccm", "mu",
                    "risk_score", "dd", "edf", "pit_pd", "ttc_pd", "sp_rating",
                    "off_grid", "neg_drift", "error")},
            })

        # Third source, for the columns it publishes. Two diagnostics, since it
        # publishes no inputs: our realized equity volatility over the same
        # window, and the debt level its own (A, sigma, DD) triple implies.
        a_bn, sig, dd = SCREENSHOT[t]
        w = window_for(panel, None)
        sigma_E = (np.log(w["MarketCap_E"]).diff().dropna().std()
                   * math.sqrt(sig_config.TRADING_DAYS_PER_YEAR))
        rows.append({
            "ticker": t, "cell": "E_screenshot", "as_of": "unknown",
            "asset": a_bn * 1e9, "sigma_A": sig, "dd": dd,
            "our_sigma_E": sigma_E,
            "implied_D": a_bn * 1e9 / math.exp(dd * sig),
            "D_used": float(w["DefaultPointDebt_D"].iloc[-1]),
        })

    df = pd.DataFrame(rows)

    # Grid coverage for the peer's reported (CCM, mu), judged on our axes.
    try:
        tables = conversion.load_tables()
        lo_c, hi_c = float(tables.ccm_axis.min()), float(tables.ccm_axis.max())
        lo_m, hi_m = float(tables.mu_axis.min()), float(tables.mu_axis.max())
        mask = df.cell == "D_theirs_reported"
        df.loc[mask, "off_grid"] = (
            ~df.loc[mask, "ccm"].between(lo_c, hi_c)
            | ~df.loc[mask, "mu"].between(lo_m, hi_m))
    except FileNotFoundError:
        pass

    df.to_csv(OUT_CSV, index=False)

    # Decomposition on DD, the headline comparable number.
    print(f"\nwrote {OUT_CSV}  ({len(df)} rows)\n")
    piv = df[df.cell.isin(["A_ours", "B_our_model_their_inputs",
                           "C_their_conv_our_inputs", "D_theirs_reported",
                           "E_screenshot"])].pivot(index="ticker", columns="cell", values="dd")
    piv = piv.reindex(TICKERS)
    piv["input_effect_B_minus_A"] = piv["B_our_model_their_inputs"] - piv["A_ours"]
    piv["convention_effect_C_minus_A"] = piv["C_their_conv_our_inputs"] - piv["A_ours"]
    piv["residual_D_minus_B"] = piv["D_theirs_reported"] - piv["B_our_model_their_inputs"]
    print("DD decomposition")
    print(piv.round(2).to_string())

    neg = df[(df.cell.isin(["A_ours", "D_theirs_reported"])) & (df.drift < 0)]
    print("\nnegative drift (Prop. 4.4.1 assumption violated):")
    for cell, grp in neg.groupby("cell"):
        print(f"  {cell}: {len(grp)}/10 -> {sorted(grp.ticker)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

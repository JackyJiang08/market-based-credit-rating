"""The tidy long table: a single flat fact table consolidating every company
and the macro rates, for databases / BI / pivot analysis.

Schema: [Ticker, AsOf, Category, Period, Metric, Value]
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from ..data import provenance as lineage
from ..data.company import CompanyData
from . import config, records

LOG = logging.getLogger(__name__)

LONG_COLUMNS = ["Ticker", "AsOf", "Category", "Period", "Metric", "Value"]


def _melt_statement(df: pd.DataFrame, ticker: str, as_of: str, category: str) -> pd.DataFrame:
    """Melt a statement frame (rows=line items, cols=period dates) to long."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LONG_COLUMNS)
    t = df.copy()
    # Normalise period-end columns to date strings (keeps parquet/CSV consistent).
    t.columns = pd.to_datetime(t.columns, errors="coerce").strftime("%Y-%m-%d")
    t.index.name = "Metric"
    long = t.reset_index().melt(id_vars="Metric", var_name="Period", value_name="Value")
    long["Ticker"], long["AsOf"], long["Category"] = ticker, as_of, category
    return long[LONG_COLUMNS]


def _melt_timeseries(df: pd.DataFrame, ticker: str, as_of: str, category: str) -> pd.DataFrame:
    """Melt a time-indexed frame (rows=dates, cols=metrics) to long."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LONG_COLUMNS)
    t = df.copy()
    t.index.name = "Period"
    long = t.reset_index().melt(id_vars="Period", var_name="Metric", value_name="Value")
    long["Period"] = pd.to_datetime(long["Period"], errors="coerce").dt.strftime("%Y-%m-%d")
    long["Ticker"], long["AsOf"], long["Category"] = ticker, as_of, category
    return long[LONG_COLUMNS]


def build_long_table(companies: list[CompanyData], rates: pd.DataFrame) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for c in companies:
        snapshot = {
            "MarketCap": c.market_cap,
            "ReferenceShares": c.reference_shares,
            "LastClose": c.last_close,
            "DividendRate": c.dividend_rate,
            "DividendYield": c.dividend_yield,
        }
        parts.append(
            pd.DataFrame(
                [
                    (c.ticker, c.as_of, "company_info", c.as_of[:10], k, v)
                    for k, v in snapshot.items()
                    if v is not None
                ],
                columns=LONG_COLUMNS,
            )
        )
        parts.append(_melt_timeseries(c.prices, c.ticker, c.as_of, "price"))
        parts.append(_melt_timeseries(c.panel, c.ticker, c.as_of, "aligned_panel"))
        parts.append(_melt_timeseries(c.dividends, c.ticker, c.as_of, "dividend"))
        parts.append(_melt_statement(c.debt_schedule, c.ticker, c.as_of, "debt_schedule"))
        parts.append(_melt_statement(c.q_income, c.ticker, c.as_of, "income_statement (Q)"))
        parts.append(_melt_statement(c.q_balance, c.ticker, c.as_of, "balance_sheet (Q)"))
        parts.append(_melt_statement(c.q_cashflow, c.ticker, c.as_of, "cash_flow (Q)"))
        parts.append(_melt_statement(c.a_income, c.ticker, c.as_of, "income_statement (A)"))
        parts.append(_melt_statement(c.a_balance, c.ticker, c.as_of, "balance_sheet (A)"))
        parts.append(_melt_statement(c.a_cashflow, c.ticker, c.as_of, "cash_flow (A)"))
        if c.sigma_A is not None:
            # Projected from the shared record so this table cannot drift from
            # the Asset sheet. Numeric fields only -- the long table coerces
            # Value to numeric and drops what does not convert.
            r = records.credit_record(c)
            measures = {
                "sigma_A": r["sigma_A"],
                "eta_A": r["eta_A"],
                "AssetValue_A": r["asset_value"],
                "R": r["drift"],
                "CCM": r["ccm"],
                "mu": r["mu"],
                "TiC": r["tic"],
                "RiskScore": r["risk_score"],
                "lambda": r["lam"],
                "DD": r["dd"],
                "EDF": r["edf"],
                "PIT_PD": r["pit_pd"],
                "TTC_PD": r["ttc_pd"],
                "Outlook": r["outlook"],
            }
            parts.append(
                pd.DataFrame(
                    [
                        (c.ticker, c.as_of, "credit_measures", c.as_of[:10], k, v)
                        for k, v in measures.items()
                        if v is not None
                    ],
                    columns=LONG_COLUMNS,
                )
            )

    if rates is not None and not rates.empty:
        r = rates.rename(columns={"Date": "Period"}).copy()
        r["Period"] = pd.to_datetime(r["Period"]).dt.strftime("%Y-%m-%d")
        r_long = r.melt(id_vars="Period", var_name="Metric", value_name="Value")
        r_long["Ticker"], r_long["AsOf"], r_long["Category"] = (
            "MACRO",
            lineage.RUN_TIMESTAMP,
            "rate",
        )
        parts.append(r_long[LONG_COLUMNS])

    if not parts:
        return pd.DataFrame(columns=LONG_COLUMNS)
    out = pd.concat(parts, ignore_index=True)
    out["Value"] = pd.to_numeric(out["Value"], errors="coerce")
    out = out.dropna(subset=["Value"])
    return out.sort_values(["Ticker", "Category", "Period", "Metric"]).reset_index(drop=True)


def write_long_table(long_df: pd.DataFrame) -> None:
    if long_df.empty:
        LOG.warning("long table is empty -- nothing written")
        return
    csv_path = os.path.join(config.OUTPUT_DIR, "all_companies_long.csv")
    long_df.to_csv(csv_path, index=False)
    LOG.info("tidy long table -> %s (%d rows)", os.path.basename(csv_path), len(long_df))
    try:
        pq_path = os.path.join(config.OUTPUT_DIR, "all_companies_long.parquet")
        long_df.to_parquet(pq_path, index=False)
        LOG.info("tidy long table -> %s", os.path.basename(pq_path))
    except (OSError, ImportError, ValueError) as exc:
        # An artifact the caller asked for does not exist. CSV is still there,
        # but that is a degraded result, not an informational note.
        LOG.warning(
            "parquet NOT written to %s (%s); only CSV is available", config.OUTPUT_DIR, exc
        )

"""Canary tests: the aligned panel must never use future information.

These are offline (synthetic fixtures) so they enforce the TIMING_PROTOCOL
invariant `max(feature.available_at) <= decision_time_t` without network access.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data_cleaning.alignment import build_panel


def _balance_sheet() -> pd.DataFrame:
    """yfinance-style balance sheet: rows = line items, cols = statement dates."""
    q1, q2 = pd.Timestamp("2024-03-31"), pd.Timestamp("2024-06-30")
    return pd.DataFrame({
        q1: {"Total Debt": 300.0, "Current Debt": 100.0, "Long Term Debt": 200.0},
        q2: {"Total Debt": 360.0, "Current Debt": 120.0, "Long Term Debt": 240.0},
    })


def _prices(dividend_date: str | None = None, dividend: float = 0.0) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", "2024-09-30")
    df = pd.DataFrame({"Close": 50.0, "Adj Close": 50.0, "Dividends": 0.0}, index=idx)
    if dividend_date is not None:
        df.loc[pd.Timestamp(dividend_date), "Dividends"] = dividend
    return df


def _rates() -> pd.Series:
    # Percent units (build_panel divides by 100).
    return pd.Series([5.0, 5.2],
                     index=[pd.Timestamp("2024-01-01"), pd.Timestamp("2024-05-15")])


def test_debt_uses_prior_statement_not_future():
    panel = build_panel(_prices(), 1000.0, _balance_sheet(), _rates())

    # Before the first statement date there is no prior data, so the raw
    # as-of debt is NaN (the future Q1 statement must NOT be pulled backward).
    assert np.isnan(panel.loc[pd.Timestamp("2024-02-01"), "ShortTermDebt"])
    assert np.isnan(panel.loc[pd.Timestamp("2024-02-01"), "LongTermDebt"])

    # Between Q1 and Q2 statements, the Q1 (prior) statement applies.
    row_may = panel.loc[pd.Timestamp("2024-05-01")]
    assert row_may["ShortTermDebt"] == 100.0
    assert row_may["LongTermDebt"] == 200.0
    assert row_may["DefaultPointDebt_D"] == 100.0 + 0.5 * 200.0  # 200

    # After Q2, the Q2 statement applies.
    row_jul = panel.loc[pd.Timestamp("2024-07-01")]
    assert row_jul["ShortTermDebt"] == 120.0
    assert row_jul["DefaultPointDebt_D"] == 120.0 + 0.5 * 240.0  # 240


def test_every_row_only_sees_past_statements():
    balance = _balance_sheet()
    stmt_dates = sorted(pd.to_datetime(balance.columns))
    panel = build_panel(_prices(), 1000.0, balance, _rates())

    st_by_stmt = {pd.Timestamp("2024-03-31"): 100.0, pd.Timestamp("2024-06-30"): 120.0}
    for t, st in panel["ShortTermDebt"].items():
        prior = [d for d in stmt_dates if d <= t]
        if not prior:
            assert np.isnan(st)
        else:
            assert st == st_by_stmt[prior[-1]]  # latest statement <= t, never future


def test_rate_is_as_of_backward():
    panel = build_panel(_prices(), 1000.0, _balance_sheet(), _rates())
    # 2024-05-01 precedes the 2024-05-15 observation -> earlier rate (5.0%).
    assert panel.loc[pd.Timestamp("2024-05-01"), "RiskFree_R"] == pytest.approx(0.05)
    # 2024-06-03 is after 2024-05-15 -> updated rate (5.2%).
    assert panel.loc[pd.Timestamp("2024-06-03"), "RiskFree_R"] == pytest.approx(0.052)


def test_dividend_add_back_lifts_equity_level():
    plain = build_panel(_prices(), 1000.0, _balance_sheet(), _rates())
    with_div = build_panel(_prices("2024-04-01", 2.0), 1000.0, _balance_sheet(), _rates())

    # Before the ex-date the two series match; after, the dividend is added back.
    assert with_div.loc[pd.Timestamp("2024-03-15"), "MarketCap_E"] == \
        plain.loc[pd.Timestamp("2024-03-15"), "MarketCap_E"]
    assert with_div.loc[pd.Timestamp("2024-05-01"), "MarketCap_E"] > \
        plain.loc[pd.Timestamp("2024-05-01"), "MarketCap_E"]
    # Add-back is exactly shares * dividend once the ex-date has passed.
    diff = (with_div.loc[pd.Timestamp("2024-05-01"), "MarketCap_E"]
            - plain.loc[pd.Timestamp("2024-05-01"), "MarketCap_E"])
    assert abs(diff - 1000.0 * 2.0) < 1e-6

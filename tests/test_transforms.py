"""Layer 2 transform tests: debt splitting and the default point.

`split_term_debt` and `default_point_debt` between them decide `D`, the model's
strike. A wrong `D` moves every downstream number, and both functions carry
fallbacks that had no coverage at all -- the `max(Total - LT, 0)` branch is what
produces `ShortTermDebt = 0` for banks and drove a 36% default-point difference
against a peer implementation on PNC.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from creditrating.data import cleaning as transforms
from creditrating.data import cleaning_config as clean_config


def _balance(rows: dict[str, list[float]], periods: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, index=periods).T


# --- split_term_debt: the happy path ----------------------------------------
def test_split_uses_reported_short_and_long_term_debt():
    bal = _balance(
        {"Current Debt": [100.0], "Long Term Debt": [900.0], "Total Debt": [1000.0]},
        ["2026-03-31"],
    )
    out = transforms.split_term_debt(bal)
    assert out["ShortTermDebt"].iloc[0] == 100.0
    assert out["LongTermDebt"].iloc[0] == 900.0


def test_long_term_prefers_the_lease_inclusive_row():
    """We take `Long Term Debt And Capital Lease Obligation` over plain LT.

    This is the documented field choice (docs/reconciliation/REPORT.md B3) and
    the single largest input difference against the peer implementation --
    90,814M on AMZN. Pinning it means the choice cannot be changed silently.
    """
    bal = _balance(
        {
            "Current Debt": [100.0],
            "Long Term Debt And Capital Lease Obligation": [900.0],
            "Long Term Debt": [600.0],
            "Total Debt": [1000.0],
        },
        ["2026-03-31"],
    )
    out = transforms.split_term_debt(bal)
    assert out["LongTermDebt"].iloc[0] == 900.0, "must include capital leases"


# --- split_term_debt: the fallbacks -----------------------------------------
def test_missing_short_term_falls_back_to_total_minus_long():
    """The bank case. No current-debt row exists, so ST = max(Total - LT, 0).

    For PNC the source reports Total = LT = 66,666 and no current debt at all,
    so this yields ST = 0 and D = 0.5 * 66,666 -- 36% below the peer's split.
    The fallback is defensible; going unnoticed is not.
    """
    bal = _balance({"Long Term Debt": [66666.0], "Total Debt": [66666.0]}, ["2026-03-31"])
    out = transforms.split_term_debt(bal)
    assert out["ShortTermDebt"].iloc[0] == 0.0
    assert out["LongTermDebt"].iloc[0] == 66666.0

    d = transforms.default_point_debt(out["ShortTermDebt"], out["LongTermDebt"])
    assert d.iloc[0] == pytest.approx(0.5 * 66666.0)


def test_missing_long_term_falls_back_to_total_minus_short():
    bal = _balance({"Current Debt": [250.0], "Total Debt": [1000.0]}, ["2026-03-31"])
    out = transforms.split_term_debt(bal)
    assert out["ShortTermDebt"].iloc[0] == 250.0
    assert out["LongTermDebt"].iloc[0] == 750.0


def test_fallbacks_never_produce_negative_debt():
    """Total below the reported leg would give a negative complement."""
    bal = _balance({"Long Term Debt": [900.0], "Total Debt": [400.0]}, ["2026-03-31"])
    out = transforms.split_term_debt(bal)
    assert out["ShortTermDebt"].iloc[0] == 0.0, "clipped at zero, not negative"


def test_empty_balance_sheet_yields_an_empty_frame():
    out = transforms.split_term_debt(pd.DataFrame())
    assert out.empty
    assert list(out.columns) == ["ShortTermDebt", "LongTermDebt"]


# --- default_point_debt -----------------------------------------------------
def test_default_point_is_short_plus_half_long():
    st = pd.Series([100.0]), pd.Series([200.0])
    d = transforms.default_point_debt(*st)
    assert d.iloc[0] == pytest.approx(100.0 + 0.5 * 200.0)
    assert clean_config.SHORT_TERM_DEBT_WEIGHT == 1.0
    assert clean_config.LONG_TERM_DEBT_WEIGHT == 0.5


def test_one_missing_leg_is_treated_as_zero():
    d = transforms.default_point_debt(pd.Series([np.nan]), pd.Series([200.0]))
    assert d.iloc[0] == pytest.approx(100.0)
    d = transforms.default_point_debt(pd.Series([100.0]), pd.Series([np.nan]))
    assert d.iloc[0] == pytest.approx(100.0)


def test_both_legs_missing_yields_nan_not_zero():
    """The #3 root cause: filling with 0 asserts the firm had no debt.

    A zero `D` is a valid-looking number that silently passed the EM step's
    `D > 0` filter as a *drop*, truncating the drift window to the balance-sheet
    history. NaN says 'unknown', which is what it is.
    """
    d = transforms.default_point_debt(pd.Series([np.nan]), pd.Series([np.nan]))
    assert np.isnan(d.iloc[0]), "missing debt must be NaN, never 0"


def test_pre_statement_rows_are_nan_and_post_statement_rows_are_not():
    st = pd.Series([np.nan, np.nan, 100.0, 100.0])
    lt = pd.Series([np.nan, np.nan, 200.0, 200.0])
    d = transforms.default_point_debt(st, lt)
    assert np.isnan(d.iloc[0]) and np.isnan(d.iloc[1])
    assert d.iloc[2] == pytest.approx(200.0) and d.iloc[3] == pytest.approx(200.0)


# --- union_balance_sheets ---------------------------------------------------
def test_union_keeps_quarterly_on_a_shared_period_end():
    q = _balance({"Total Debt": [100.0]}, ["2026-03-31"])
    a = _balance({"Total Debt": [999.0]}, ["2026-03-31"])
    out = transforms.union_balance_sheets(q, a)
    assert out.loc["Total Debt", "2026-03-31"] == 100.0, "quarterly is the finer obs"


def test_union_adds_annual_periods_the_quarterly_sheet_does_not_reach():
    q = _balance({"Total Debt": [100.0]}, ["2026-03-31"])
    a = _balance({"Total Debt": [80.0]}, ["2023-12-31"])
    out = transforms.union_balance_sheets(q, a)
    assert set(out.columns) == {"2026-03-31", "2023-12-31"}
    assert out.columns[0] == "2026-03-31", "columns stay newest-first"
    assert out.loc["Total Debt", "2023-12-31"] == 80.0


def test_union_handles_either_side_being_empty():
    q = _balance({"Total Debt": [100.0]}, ["2026-03-31"])
    assert transforms.union_balance_sheets(q, pd.DataFrame()).equals(q)
    assert transforms.union_balance_sheets(pd.DataFrame(), q).equals(q)

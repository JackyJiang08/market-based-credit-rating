"""Submission workbook schema tests (offline; writes to a temp dir).

The Asset sheet is the deliverable's contract, so its column set is pinned as a
golden file rather than spot-checked. Adding, removing, renaming or reordering a
column is a deliberate act that has to change the golden list here.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from data_cleaning.company import CompanyData
from dashboard import records, submission

# --- GOLDEN: the exact Asset sheet, in order. -------------------------------
# First 23 entries are the reference workbook's canonical `Asset` columns; the
# last two are deliberate additions (see dashboard/records.py). Do not edit to
# make a test pass -- edit only when the deliverable's contract really changes.
GOLDEN_ASSET_SCHEMA = (
    "Company", "Symbol", "Shares Outstanding", "Last Date", "Last Price",
    "Last Statement Date", "Debt/Short Term", "Debt/Long Term", "Total Debt",
    "Interest Rate", "sigma", "A", "R", "eta", "CCM", "mu", "TiC Risk Score",
    "DD", "EDF", "PIT PD", "TTC PD", "SP Rating", "Outlook",
    "lambda", "Rating Basis",
)

GOLDEN_VALIDATION_SCHEMA = (
    "Symbol", "Data Status", "EM converged", "EM iters", "sigma_A",
    "Drift regime", "Drift SE", "Drift span (y)", "Rating basis",
    "TTC at floor", "Off-grid", "Statement available at", "Availability method",
    "Warnings",
)


def _minimal_company() -> CompanyData:
    idx = pd.bdate_range("2024-01-02", periods=60)
    panel = pd.DataFrame(
        {"ShortTermDebt": 100.0, "LongTermDebt": 200.0, "RiskFree_R": 0.04,
         "DefaultPointDebt_D": 200.0, "MarketCap_E": 5.0e4},
        index=idx)
    c = CompanyData(ticker="TST", name="Test Co")
    c.panel = panel
    c.debt_schedule = pd.DataFrame({"2024-06-30": [300.0]}, index=["Total Debt"])
    c.reference_shares, c.last_close = 1000.0, 50.0
    c.sigma_A, c.eta_A, c.asset_value = 0.25, 0.08, 2.5e5
    c.em_iters, c.em_converged = 3, True
    c.mu, c.ccm, c.tic, c.risk_score = 12.0, 1.5, 0.12, 12.0
    c.lam = (1.5 + 1.0) ** -1.5
    c.dd, c.edf, c.pit_pd = 2.5, 0.006, 0.05
    c.ttc_pd, c.sp_rating, c.outlook, c.rating_off_grid = 0.01, "BB", 0.04, False
    c.rating_basis, c.ttc_at_floor = "GRID_INTERIOR", False
    c.drift_regime, c.drift_se, c.drift_span_years = "VALID", 0.11, 5.0
    c.data_status = "OK"
    return c


# --- Golden schema ----------------------------------------------------------
def test_asset_schema_constant_matches_the_golden_list():
    assert records.ASSET_SCHEMA == GOLDEN_ASSET_SCHEMA


def test_validation_schema_constant_matches_the_golden_list():
    assert records.VALIDATION_SCHEMA == GOLDEN_VALIDATION_SCHEMA


def test_canonical_prefix_is_the_reference_workbooks_23_columns():
    """The reference `Asset` sheet is 23 columns; ours must start with exactly them."""
    assert len(records.CANONICAL_ASSET_COLUMNS) == 23
    assert records.ASSET_SCHEMA[:23] == records.CANONICAL_ASSET_COLUMNS


def test_written_sheet_carries_exactly_the_schema_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "OUTPUT_DIR", str(tmp_path))
    path = submission.write_submission([_minimal_company()])

    asset = pd.read_excel(path, "Asset")
    assert tuple(asset.columns) == GOLDEN_ASSET_SCHEMA

    validation = pd.read_excel(path, "validation")
    assert tuple(validation.columns) == GOLDEN_VALIDATION_SCHEMA


# --- The specific defects #7 was opened for ---------------------------------
def test_asset_sheet_carries_the_asset_value():
    """`A` was absent from the Asset sheet entirely (#7)."""
    assert "A" in records.ASSET_SCHEMA
    row = records.asset_row(_minimal_company())
    assert row["A"] == pytest.approx(2.5e5)


def test_tic_risk_score_is_one_column_not_two():
    """The reference sheet has a single `TiC Risk Score`; we emitted two (#7)."""
    assert "TiC Risk Score" in records.ASSET_SCHEMA
    assert "TiC" not in records.ASSET_SCHEMA
    assert "Risk Score" not in records.ASSET_SCHEMA
    row = records.asset_row(_minimal_company())
    assert row["TiC Risk Score"] == pytest.approx(12.0)


def test_lambda_reaches_the_deliverable():
    """lambda (Eq. 3/6) was computed in measures.py and reached no output (#8)."""
    assert "lambda" in records.ASSET_SCHEMA
    row = records.asset_row(_minimal_company())
    assert row["lambda"] == pytest.approx((1.5 + 1.0) ** -1.5)


def test_em_iters_is_a_diagnostic_not_a_deliverable_column():
    assert "EM iters" not in records.ASSET_SCHEMA
    assert "EM iters" in records.VALIDATION_SCHEMA


# --- Values -----------------------------------------------------------------
def test_asset_row_values(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "OUTPUT_DIR", str(tmp_path))
    path = submission.write_submission([_minimal_company()])
    asset = pd.read_excel(path, "Asset")

    assert asset.loc[0, "Symbol"] == "TST"
    assert asset.loc[0, "Total Debt"] == 300.0
    # R is the realized drift = eta - sigma^2/2 (the term inside DD).
    assert asset.loc[0, "R"] == pytest.approx(0.08 - 0.5 * 0.25 ** 2)
    assert asset.loc[0, "Rating Basis"] == "GRID_INTERIOR"

    validation = pd.read_excel(path, "validation")
    assert validation.loc[0, "EM converged"] in (True, "True")
    assert validation.loc[0, "Drift regime"] == "VALID"


def test_unrated_company_leaves_the_rating_cells_empty_and_says_why(tmp_path,
                                                                   monkeypatch):
    """An OFF_GRID company must be blank in the rating cells, not zero-filled."""
    monkeypatch.setattr(submission, "OUTPUT_DIR", str(tmp_path))
    c = _minimal_company()
    c.ttc_pd, c.sp_rating, c.outlook = float("nan"), None, None
    c.rating_basis, c.rating_off_grid = "OFF_GRID", True
    path = submission.write_submission([c])

    asset = pd.read_excel(path, "Asset")
    assert math.isnan(asset.loc[0, "TTC PD"])
    assert pd.isna(asset.loc[0, "SP Rating"])
    assert asset.loc[0, "Rating Basis"] == "OFF_GRID"

    validation = pd.read_excel(path, "validation")
    assert "outside the conversion grid" in validation.loc[0, "Warnings"]


# --- One writer (#8) --------------------------------------------------------
def test_all_writers_project_from_the_same_record():
    """No writer may re-derive a credit field; all read dashboard.records."""
    import inspect

    from dashboard import excel, longtable

    for module in (submission, excel, longtable):
        src = inspect.getsource(module)
        assert "records." in src, f"{module.__name__} does not use dashboard.records"

    # The shared record is the only place these are assembled.
    r = records.credit_record(_minimal_company())
    for key in ("asset_value", "risk_score", "lam", "ccm", "mu", "drift",
                "rating_basis", "drift_regime"):
        assert key in r
